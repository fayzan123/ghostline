"""
sheets.py — Google Sheets integration for the Ghostline lead generation tool.
"""

import logging

import gspread
from models import Lead
from config import SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, GOOGLE_SHEET_HEADERS

logger = logging.getLogger(__name__)


def connect_to_sheet() -> tuple[gspread.Spreadsheet, gspread.Worksheet]:
    """
    Connect to Google Sheets via service account credentials.

    Uses gspread.service_account(filename=SERVICE_ACCOUNT_FILE) and opens
    the sheet by SPREADSHEET_ID. Returns both the spreadsheet and sheet1 worksheet.

    Returns:
        Tuple of (Spreadsheet, Worksheet) objects.

    Raises:
        FileNotFoundError: If SERVICE_ACCOUNT_FILE does not exist.
        gspread.exceptions.SpreadsheetNotFound: If SPREADSHEET_ID is wrong.
    """
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    sheet = gc.open_by_key(SPREADSHEET_ID)
    worksheet = sheet.sheet1

    logger.info(
        "Connected to Google Sheet: '%s' (id=%s)",
        sheet.title,
        SPREADSHEET_ID,
    )

    return sheet, worksheet


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
    Converts remaining Lead objects to rows via lead.to_row().
    Uses worksheet.append_rows(rows, value_input_option='USER_ENTERED') for
    a single batch API call regardless of lead count.

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
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")
        logger.info("Appended %d new leads to Google Sheet.", len(rows))
    else:
        logger.info("No new leads to append.")

    return len(rows)
