"""
sheets.py — Google Sheets integration for the Ghostline lead generation tool.

Handles authentication, header validation, deduplication reads, batch writes,
and Sheets API rate limit handling.
"""

import logging
import time

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound
from models import Lead
from config import SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, GOOGLE_SHEET_HEADERS

logger = logging.getLogger(__name__)

# Google Sheets API: 100 requests per 100 seconds per user.
# Sleep this long after every write to stay safely under the limit.
_SHEETS_WRITE_COOLDOWN = 1.5  # seconds
_SHEETS_RETRY_WAIT = 30  # seconds on quota exceeded (429)
_SHEETS_MAX_RETRIES = 3


def connect_to_sheet() -> tuple[gspread.Spreadsheet, gspread.Worksheet]:
    """
    Connect to Google Sheets via service account credentials.

    Uses gspread.service_account(filename=SERVICE_ACCOUNT_FILE) and opens
    the sheet by SPREADSHEET_ID. Returns both the spreadsheet and sheet1 worksheet.

    If the sheet is empty (no rows at all), writes the header row first.

    Returns:
        Tuple of (Spreadsheet, Worksheet) objects.

    Raises:
        FileNotFoundError: If SERVICE_ACCOUNT_FILE does not exist.
        gspread.exceptions.SpreadsheetNotFound: If SPREADSHEET_ID is wrong.
        RuntimeError: If credentials are invalid or authentication fails.
    """
    try:
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Service account file not found: {SERVICE_ACCOUNT_FILE}. "
            "See CHOX_LEAD_GEN_PLAN.md Section 9.4 for setup instructions."
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to authenticate with Google Sheets: {exc}. "
            "Check that the service account JSON is valid."
        ) from exc

    try:
        sheet = gc.open_by_key(SPREADSHEET_ID)
    except SpreadsheetNotFound:
        raise SpreadsheetNotFound(
            f"Spreadsheet not found for ID: {SPREADSHEET_ID}. "
            "Check SPREADSHEET_ID in .env and that the sheet is shared with "
            "the service account email."
        )

    worksheet = sheet.sheet1

    logger.info(
        "Connected to Google Sheet: '%s' (id=%s)",
        sheet.title,
        SPREADSHEET_ID,
    )

    # Ensure header row exists
    _ensure_headers(worksheet)

    return sheet, worksheet


def _ensure_headers(worksheet: gspread.Worksheet) -> None:
    """
    If the sheet is empty or the first row doesn't match GOOGLE_SHEET_HEADERS,
    write the header row.
    """
    try:
        row1 = worksheet.row_values(1)
    except APIError as exc:
        logger.warning("Failed to read row 1 for header check: %s", exc)
        row1 = []

    if not row1:
        logger.info("Sheet is empty — writing header row.")
        _retry_write(
            lambda: worksheet.update('A1', [GOOGLE_SHEET_HEADERS], value_input_option="RAW")
        )
    elif row1 != GOOGLE_SHEET_HEADERS:
        logger.warning(
            "Header row mismatch. Expected %d columns, found %d. "
            "First header: '%s' (expected 'github_username'). "
            "Proceeding without overwriting — data may not align.",
            len(GOOGLE_SHEET_HEADERS),
            len(row1),
            row1[0] if row1 else "(empty)",
        )
    else:
        logger.debug("Header row validated — %d columns.", len(row1))


def load_existing_usernames(worksheet: gspread.Worksheet) -> set:
    """
    Load all existing github_username values from column A of the sheet.

    Uses worksheet.col_values(1) for a single API call. Converts to a Python
    set for O(1) deduplication lookups. Strips the header row value.

    Args:
        worksheet: gspread Worksheet object (sheet1)

    Returns:
        Set of github_username strings already in the sheet. Excludes header.
    """
    values = worksheet.col_values(1)  # Column A = github_username

    # Strip header row if present
    if values and values[0] == "github_username":
        values = values[1:]

    existing = set(values)
    logger.info("Loaded %d existing usernames from sheet.", len(existing))

    return existing


def append_leads(worksheet: gspread.Worksheet, leads: list[Lead], existing_users: set) -> int:
    """
    Deduplicate and batch-append new leads to the Google Sheet.

    Filters out any leads whose github_username is in existing_users.
    Also deduplicates within the current batch.
    Converts remaining Lead objects to rows via lead.to_row().
    Uses worksheet.append_rows(rows, value_input_option='USER_ENTERED') for
    a single batch API call regardless of lead count.

    Retries on Sheets API quota errors (HTTP 429) with exponential backoff.

    Args:
        worksheet: gspread Worksheet object
        leads: List of scored Lead objects from score_leads()
        existing_users: Set of usernames already in sheet (from load_existing_usernames)

    Returns:
        Count of new leads successfully appended.
    """
    rows = []
    seen_in_batch = set()

    for lead in leads:
        username = lead.github_username

        # Skip if already in the sheet
        if username in existing_users:
            logger.debug("Skipping %s — already in sheet.", username)
            continue

        # Skip if duplicate within this batch
        if username in seen_in_batch:
            logger.debug("Skipping %s — duplicate in current batch.", username)
            continue

        seen_in_batch.add(username)
        rows.append(lead.to_row())

    if rows:
        _retry_write(
            lambda: worksheet.append_rows(rows, value_input_option="USER_ENTERED")
        )
        logger.info("Appended %d new leads to Google Sheet.", len(rows))
    else:
        logger.info("No new leads to append.")

    return len(rows)


def _retry_write(write_fn, max_retries: int = _SHEETS_MAX_RETRIES) -> None:
    """
    Execute a Sheets write operation with retry on quota exceeded (429).

    Args:
        write_fn: Callable that performs the write (no args).
        max_retries: Max retry attempts on 429 errors.

    Raises:
        gspread.exceptions.APIError: If retries are exhausted or non-429 error.
    """
    for attempt in range(1, max_retries + 1):
        try:
            write_fn()
            time.sleep(_SHEETS_WRITE_COOLDOWN)
            return
        except APIError as exc:
            # gspread wraps HTTP errors — check for 429 (quota exceeded)
            status_code = getattr(exc, "code", None) or getattr(
                getattr(exc, "response", None), "status_code", None
            )

            if status_code == 429:
                wait = _SHEETS_RETRY_WAIT * attempt
                logger.warning(
                    "Sheets API quota exceeded (429). Retry %d/%d in %ds.",
                    attempt,
                    max_retries,
                    wait,
                )
                time.sleep(wait)
                continue

            # Non-429 API error — don't retry
            logger.error("Sheets API error (HTTP %s): %s", status_code, exc)
            raise

    logger.error("Sheets API write failed after %d retries.", max_retries)
    raise RuntimeError(f"Google Sheets API write failed after {max_retries} retries (quota exceeded).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=== sheets.py self-test ===\n")

    # Step 1: Connect
    print("Connecting to Google Sheet...")
    spreadsheet, worksheet = connect_to_sheet()
    print(f"  Connected: '{spreadsheet.title}'\n")

    # Step 2: Load existing usernames
    existing = load_existing_usernames(worksheet)
    print(f"  Existing usernames: {len(existing)}\n")

    # Step 3: Write a mock lead
    mock_lead = Lead(
        github_username="__ghostline_test__",
        email="test@ghostline-test.example",
        full_name="Ghostline Test Lead",
        repo_url="https://github.com/__ghostline_test__/test-repo",
        repo_name="__ghostline_test__/test-repo",
        repo_description="Automated test row — safe to delete",
        repo_stars=0,
        repo_language="Python",
        frameworks_detected="langchain",
        lead_score=42,
        lead_tier="tier_2",
        inferred_pain_point="blind_tool_calls",
        run_id="test-run",
    )

    print("Writing mock lead...")
    count = append_leads(worksheet, [mock_lead], existing)
    print(f"  Appended: {count}\n")

    # Step 4: Read back to confirm
    print("Reading back column A to confirm...")
    updated = load_existing_usernames(worksheet)
    if "__ghostline_test__" in updated:
        print("  SUCCESS: test lead found in sheet.\n")
        print("  NOTE: Manually delete the '__ghostline_test__' row from the sheet.")
    else:
        print("  WARNING: test lead NOT found after write. Check sheet manually.")
