"""
sheets.py — Google Sheets integration for the Ghostline lead generation tool.
"""

import gspread
from models import Lead
from config import SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, GOOGLE_SHEET_HEADERS


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
    pass


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
    pass


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
    pass
