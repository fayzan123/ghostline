"""
review_cli.py — Interactive terminal review CLI for the Ghostline outreach agent.

Public API:
    review_batch(drafts) -> list[dict]

        Receives the list of EmailDraft dicts from the LangGraph state snapshot
        and collects one human decision per draft.  Returns a list of decision
        dicts of the same length as `drafts`, preserving index alignment so that
        process_approval can use a simple index lookup.

Decision dict schema:
    {
        "index":        int,   # position in drafts list (0-based)
        "action":       str,   # "approve" | "reject" | "edit" | "quit"
        "edited_body":  str,   # non-empty only when action == "edit"
    }

Design decisions:
  - Single keypress without requiring Enter is implemented via termios/tty raw
    mode.  This only works on Unix-like systems (macOS, Linux).  The function
    restores terminal settings in a finally block so a crash or Ctrl-C cannot
    leave the terminal in a broken state.
  - Drafts with status == "failed" are auto-skipped.  The decisions list still
    includes a sentinel entry for them (action="reject") so the list length
    equals len(drafts) and index alignment is preserved.
  - B (approve-batch) approves the current draft and all remaining non-failed
    drafts immediately, then returns.  The reviewer does not need to press any
    more keys.
  - Q (quit) marks the current draft and all remaining drafts (including
    failed ones) with action="quit".  The graph receives these and can
    checkpoint state for a later --resume run.
  - E (edit) opens the email body in $EDITOR (default: nano) via a temporary
    file.  The saved content replaces the body.  If the editor exits with a
    non-zero return code the edit is discarded and the reviewer is prompted
    again.
  - The display format matches the spec in Section 6.2 of OUTREACH_AGENT_PLAN.md:
    separator bar using ━, lead context block, indented subject + body.
"""

import os
import subprocess
import sys
import tempfile
import termios
import tty
from typing import List

from outreach.outreach_state import EmailDraft


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEP_CHAR = "\u2501"           # ━
_SEP_WIDTH = 54
_SEP_LINE = _SEP_CHAR * _SEP_WIDTH

_VALID_KEYS = {"a", "r", "e", "b", "q"}

_PROMPT = (
    "\nACTION: [A]pprove / [R]eject / [E]dit / approve [B]atch / [Q]uit\n> "
)


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------

def _read_single_key() -> str:
    """Block until the user presses a single key; return it lowercased.

    Uses termios/tty raw mode so no Enter is required.  Terminal settings are
    saved before entering raw mode and restored in a finally block so that a
    KeyboardInterrupt (Ctrl-C) cannot leave the terminal in a broken state.

    Raises:
        KeyboardInterrupt: if the user presses Ctrl-C (byte 0x03).
        RuntimeError: if stdin is not an interactive TTY.
    """
    if not sys.stdin.isatty():
        raise RuntimeError(
            "review_cli requires an interactive terminal (stdin is not a TTY). "
            "Run run_outreach.py directly from a terminal, not piped or redirected."
        )
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    # Ctrl-C in raw mode sends 0x03 which sys.stdin.read(1) returns as '\x03'
    if ch == "\x03":
        raise KeyboardInterrupt

    return ch.lower()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _display_draft(draft: EmailDraft, position: int, total: int) -> None:
    """Print the lead context block and full email for one draft.

    `position` is 1-based for display purposes.
    """
    ctx = draft.get("lead_context", {})

    print()
    print(_SEP_LINE)
    print(f"Email {position}/{total}")
    print(_SEP_LINE)
    print()
    print("LEAD CONTEXT:")
    print(
        f"  Name:       "
        f"{ctx.get('full_name', ctx.get('github_username', ''))}"
    )
    print(f"  Username:   {ctx.get('github_username', '')}")
    print(f"  Email:      {draft.get('to_email', '')}")
    print(
        f"  Repo:       {ctx.get('repo_name', '')} "
        f"({ctx.get('repo_stars', 0)} stars)"
    )
    print(f"  Frameworks: {ctx.get('frameworks_detected', '')}")
    print(
        f"  Score:      {ctx.get('lead_score', '')} "
        f"({ctx.get('lead_tier', '')})"
    )
    print(f"  Company:    {ctx.get('profile_company', '') or 'Independent'}")
    print()
    print("GENERATED EMAIL:")
    print(f"  Subject: {draft.get('subject', '')}")
    print()
    body = draft.get("body", "")
    for line in body.splitlines():
        print(f"  {line}")
    print()


# ---------------------------------------------------------------------------
# Editor integration
# ---------------------------------------------------------------------------

def _open_in_editor(body: str) -> str | None:
    """Open `body` in $EDITOR and return the saved content, or None on failure.

    Writes `body` to a temporary file, opens it with the user's preferred
    editor (falling back to nano), waits for the editor to exit, and reads
    the file back.

    Returns None if the editor exits with a non-zero return code, signalling
    that the edit should be discarded and the reviewer should be re-prompted.
    """
    editor = os.environ.get("EDITOR", "nano")

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        prefix="ghostline_email_",
        delete=False,
    ) as tmp:
        tmp.write(body)
        tmp_path = tmp.name

    try:
        try:
            result = subprocess.run([editor, tmp_path])
        except FileNotFoundError:
            print(
                f"\nEditor '{editor}' not found. "
                "Set $EDITOR to a valid editor binary (e.g. nano, vim) and try again. "
                "Edit discarded — please choose an action again."
            )
            return None

        if result.returncode != 0:
            print(
                f"\nEditor exited with code {result.returncode}. "
                "Edit discarded — please choose an action again."
            )
            return None

        with open(tmp_path, "r", encoding="utf-8") as f:
            saved = f.read()

        return saved

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Decision helpers
# ---------------------------------------------------------------------------

def _make_decision(index: int, action: str, edited_body: str = "") -> dict:
    return {"index": index, "action": action, "edited_body": edited_body}


def _approve_remaining(
    decisions: List[dict],
    drafts: List[EmailDraft],
    start_index: int,
) -> None:
    """Append approve decisions for all non-failed drafts from start_index onward.

    Mutates `decisions` in place.
    """
    for i in range(start_index, len(drafts)):
        draft = drafts[i]
        if draft.get("status") == "failed":
            # Auto-skip failed drafts with a reject sentinel
            decisions.append(_make_decision(i, "reject"))
        else:
            decisions.append(_make_decision(i, "approve"))


def _quit_remaining(
    decisions: List[dict],
    drafts: List[EmailDraft],
    start_index: int,
) -> None:
    """Append quit decisions for all drafts from start_index onward.

    Mutates `decisions` in place.  Quit is set for all drafts regardless of
    status so the graph receives a complete decisions list.
    """
    for i in range(start_index, len(drafts)):
        decisions.append(_make_decision(i, "quit"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def review_batch(drafts: List[EmailDraft]) -> List[dict]:
    """Collect one human decision per draft via an interactive terminal prompt.

    Args:
        drafts: The list of EmailDraft dicts from the LangGraph state snapshot.
                Drafts with status == "failed" are auto-skipped.

    Returns:
        A list of decision dicts of the same length as `drafts`.  Index
        alignment is guaranteed: decisions[i]["index"] == i for all i.

    Raises:
        KeyboardInterrupt: propagated from _read_single_key when the user
                           presses Ctrl-C.  The caller (run_outreach.py) is
                           responsible for handling this and checkpointing.
    """
    total = len(drafts)
    decisions: List[dict] = []

    if total == 0:
        print("\nNo drafts to review.")
        return decisions

    print(f"\n{_SEP_LINE}")
    print(f"REVIEW SESSION — {total} email(s) to review")
    print(_SEP_LINE)

    i = 0
    while i < total:
        draft = drafts[i]
        position = i + 1  # 1-based for display

        # ------------------------------------------------------------------
        # Auto-skip failed drafts
        # ------------------------------------------------------------------
        if draft.get("status") == "failed":
            print()
            print(f"{_SEP_LINE}")
            print(f"Email {position}/{total}  [FAILED — auto-skipped]")
            print(f"{_SEP_LINE}")
            error_msg = draft.get("send_error", "generation failed")
            print(f"  Error: {error_msg}")
            decisions.append(_make_decision(i, "reject"))
            i += 1
            continue

        # ------------------------------------------------------------------
        # Display the draft
        # ------------------------------------------------------------------
        _display_draft(draft, position, total)

        # ------------------------------------------------------------------
        # Collect keypress — loop until a valid key is received
        # ------------------------------------------------------------------
        while True:
            print(_PROMPT, end="", flush=True)
            key = _read_single_key()
            print(key.upper())  # echo the key so the user sees what they pressed

            if key not in _VALID_KEYS:
                print(
                    f"  Invalid key '{key}'. "
                    "Press A, R, E, B, or Q."
                )
                continue

            # ---- A: Approve ----
            if key == "a":
                decisions.append(_make_decision(i, "approve"))
                i += 1
                break

            # ---- R: Reject ----
            elif key == "r":
                decisions.append(_make_decision(i, "reject"))
                i += 1
                break

            # ---- E: Edit ----
            elif key == "e":
                original_body = draft.get("body", "")
                saved_body = _open_in_editor(original_body)
                if saved_body is None:
                    # Editor failed — re-prompt without advancing
                    _display_draft(draft, position, total)
                    continue
                decisions.append(_make_decision(i, "edit", edited_body=saved_body))
                i += 1
                break

            # ---- B: Approve batch (current + all remaining) ----
            elif key == "b":
                # Approve the current draft
                decisions.append(_make_decision(i, "approve"))
                # Approve all remaining drafts (handles failed ones internally)
                _approve_remaining(decisions, drafts, start_index=i + 1)
                print(
                    f"\n  Approved email {position}/{total} and all remaining "
                    f"{total - position} email(s)."
                )
                return decisions

            # ---- Q: Quit ----
            elif key == "q":
                # Mark current and all remaining as quit
                _quit_remaining(decisions, drafts, start_index=i)
                remaining = total - position + 1
                print(
                    f"\n  Quit at email {position}/{total}. "
                    f"{remaining} email(s) marked for resume."
                )
                return decisions

    print(f"\n{_SEP_LINE}")
    print("Review complete.")
    print(_SEP_LINE)
    return decisions
