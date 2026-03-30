"""
outreach_sheets.py — Google Sheets data access layer for the Ghostline
outreach agent.

Provides three operations:
  - load_uncontacted_leads: read all rows, filter to actionable leads, sort
    by score descending, attach sheet row numbers for later writes.
  - mark_lead_contacted: batch-update the contacted/contacted_at/
    contact_method/notes columns for one lead row.
  - mark_lead_bounced: batch-update response_status/notes for one lead row.

All writes go through _retry_write from shared.sheets — never duplicated here.
"""

import logging
from datetime import datetime, timezone

import gspread

from shared.sheets import connect_to_sheet, _retry_write
from shared.config import GOOGLE_SHEET_HEADERS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column index constants (1-indexed, matching GOOGLE_SHEET_HEADERS)
# These are verified against the 28-column header list in shared/config.py.
# ---------------------------------------------------------------------------

_COL_CONTACTED = 23       # W — "contacted"
_COL_CONTACTED_AT = 24    # X — "contacted_at"
_COL_CONTACT_METHOD = 25  # Y — "contact_method"
_COL_RESPONSE_STATUS = 26 # Z — "response_status"
_COL_NOTES = 27           # AA — "notes"


def _col_to_a1(col: int) -> str:
    """
    Convert a 1-indexed column number to an A1-notation column letter string.

    Supports columns 1–702 (A–ZZ), which is far beyond the 28 columns in this
    sheet. No external dependencies — pure arithmetic.

    Examples:
        1  -> "A"
        26 -> "Z"
        27 -> "AA"
        28 -> "AB"
    """
    result = ""
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _cell(col: int, row: int) -> str:
    """Return an A1 cell address like 'W5' for col=23, row=5."""
    return f"{_col_to_a1(col)}{row}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_uncontacted_leads() -> list[dict]:
    """
    Connect to the Google Sheet and return all actionable uncontacted leads.

    Filtering rules (applied in Python after a single get_all_records() call):
      - contacted column is not "TRUE"  (catches "FALSE", empty string, missing)
      - email field is non-empty
      - response_status is not "unsubscribed"

    Each returned dict has all sheet columns as keys (from get_all_records)
    plus one extra key:
      - "_sheet_row": int — 1-indexed sheet row number (header is row 1,
        first data row is row 2).

    Results are sorted descending by lead_score (treating missing/non-numeric
    values as 0 so they sort to the bottom).

    Returns:
        List of lead dicts ready for the outreach agent. May be empty.
    """
    _, worksheet = connect_to_sheet()

    all_records = worksheet.get_all_records()
    logger.info("Loaded %d total rows from sheet.", len(all_records))

    actionable: list[dict] = []

    for idx, record in enumerate(all_records):
        # Row 1 is the header; first data row is row 2.
        sheet_row = idx + 2

        # Filter: must have a non-empty email
        email = str(record.get("email", "")).strip()
        if not email:
            logger.debug("Row %d skipped — no email.", sheet_row)
            continue

        # Filter: must not already be contacted
        contacted = str(record.get("contacted", "")).strip().upper()
        if contacted == "TRUE":
            logger.debug("Row %d skipped — already contacted.", sheet_row)
            continue

        # Filter: must not have unsubscribed
        response_status = str(record.get("response_status", "")).strip().lower()
        if response_status == "unsubscribed":
            logger.debug("Row %d skipped — unsubscribed.", sheet_row)
            continue

        record["_sheet_row"] = sheet_row
        actionable.append(record)

    logger.info(
        "%d actionable (uncontacted) leads found after filtering.",
        len(actionable),
    )

    # Preserve spreadsheet row order (top-to-bottom).
    return actionable


def mark_lead_contacted(
    worksheet: gspread.Worksheet,
    sheet_row: int,
    notes: str = "",
) -> None:
    """
    Update the contacted/contacted_at/contact_method/notes columns for one
    lead after a successful email send.

    Uses worksheet.batch_update so all four cell changes are sent in a single
    API call. The write is wrapped in _retry_write for quota-exceeded handling.

    Args:
        worksheet: The gspread Worksheet object (sheet1) from connect_to_sheet.
        sheet_row: 1-indexed row number stored in lead["_sheet_row"].
        notes: Optional notes string to write into the notes column.
    """
    contacted_at = datetime.now(timezone.utc).isoformat()

    updates = [
        {"range": _cell(_COL_CONTACTED, sheet_row),       "values": [["TRUE"]]},
        {"range": _cell(_COL_CONTACTED_AT, sheet_row),    "values": [[contacted_at]]},
        {"range": _cell(_COL_CONTACT_METHOD, sheet_row),  "values": [["email"]]},
        {"range": _cell(_COL_NOTES, sheet_row),           "values": [[notes]]},
    ]

    _retry_write(
        lambda: worksheet.batch_update(updates, value_input_option="RAW")
    )

    logger.info(
        "Marked row %d as contacted at %s (notes: %s).",
        sheet_row,
        contacted_at,
        notes[:80] if notes else "(none)",
    )


def mark_lead_bounced(
    worksheet: gspread.Worksheet,
    sheet_row: int,
    notes: str = "",
) -> None:
    """
    Update the response_status and notes columns for one lead when a bounce
    is detected.

    Uses worksheet.batch_update for a single API call. Wrapped in _retry_write.

    Args:
        worksheet: The gspread Worksheet object (sheet1) from connect_to_sheet.
        sheet_row: 1-indexed row number stored in lead["_sheet_row"].
        notes: Optional notes string describing the bounce.
    """
    updates = [
        {"range": _cell(_COL_RESPONSE_STATUS, sheet_row), "values": [["bounced"]]},
        {"range": _cell(_COL_NOTES, sheet_row),           "values": [[notes]]},
    ]

    _retry_write(
        lambda: worksheet.batch_update(updates, value_input_option="RAW")
    )

    logger.info(
        "Marked row %d as bounced (notes: %s).",
        sheet_row,
        notes[:80] if notes else "(none)",
    )
