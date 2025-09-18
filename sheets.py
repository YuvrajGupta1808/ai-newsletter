import time
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SERVICE_JSON, SCOPE, SHEET_ID, DESIRED_HEADERS

def open_sheet_with_retry(retries=3, backoff=2):
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_JSON, SCOPE)
    client = gspread.authorize(creds)
    last_err = None
    for i in range(retries):
        try:
            return client.open_by_key(SHEET_ID).sheet1
        except Exception as e:
            last_err = e
            time.sleep(backoff ** i)
    raise last_err

def ensure_headers(sheet):
    """Ensure sheet has at least DESIRED_HEADERS; append any missing to the right."""
    headers = sheet.row_values(1)
    if not headers:
        sheet.update("A1", [DESIRED_HEADERS])
        return DESIRED_HEADERS
    
    # Remove duplicates and empty strings from headers while preserving order
    seen = set()
    unique_headers = []
    for header in headers:
        if header and header.strip() and header not in seen:
            seen.add(header)
            unique_headers.append(header)
    
    # Always ensure we have our required headers
    final_headers = []
    for desired_header in DESIRED_HEADERS:
        if desired_header in unique_headers:
            final_headers.append(desired_header)
        else:
            final_headers.append(desired_header)
    
    # Add any extra headers that aren't in our desired list
    for header in unique_headers:
        if header not in DESIRED_HEADERS:
            final_headers.append(header)
    
    # Update the header row to ensure clean headers
    sheet.update("A1", [final_headers])
    return final_headers

def _col_index(headers, name):
    try:
        return headers.index(name) + 1
    except ValueError:
        return None

def upsert_subscriber(email: str, selected_topics: list, max_items: int = 3):
    """
    If 'Email' exists, update row; else append. No Name field.
    Returns ("updated"/"created", row_index or None)
    """
    sheet = open_sheet_with_retry()
    headers = ensure_headers(sheet)

    now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    row_dict = {
        "Email": email,
        "Technology": "TRUE" if "Technology" in selected_topics else "FALSE",
        "Sports":     "TRUE" if "Sports" in selected_topics else "FALSE",
        "Politics":   "TRUE" if "Politics" in selected_topics else "FALSE",
        "Finance":    "TRUE" if "Finance" in selected_topics else "FALSE",
        "Max_items":  str(max_items),
        "Timestamp":  now_iso,
    }

    email_col = _col_index(headers, "Email")
    if not email_col:
        headers = ensure_headers(sheet)
        email_col = _col_index(headers, "Email")

    # Find existing by email (case-insensitive)
    try:
        # Use get_all_records with expected headers to avoid duplicate header issues
        all_records = sheet.get_all_records(expected_headers=headers)
        for idx, record in enumerate(all_records, start=2):
            if (record.get("Email", "") or "").strip().lower() == email.strip().lower():
                row_update = [row_dict.get(h, "") for h in headers]
                sheet.update(f"A{idx}", [row_update])   # update whole row from A{idx}
                return "updated", idx
    except Exception as e:
        print(f"⚠️ Error with get_all_records, falling back to col_values: {e}")
        # Fallback to the original method
        email_cells = sheet.col_values(email_col)[1:]  # skip header
        for idx, cell_val in enumerate(email_cells, start=2):
            if (cell_val or "").strip().lower() == email.strip().lower():
                row_update = [row_dict.get(h, "") for h in headers]
                sheet.update(f"A{idx}", [row_update])   # update whole row from A{idx}
                return "updated", idx

    new_row = [row_dict.get(h, "") for h in headers]
    sheet.append_row(new_row)
    return "created", None

# --- New helpers for OTP + management flows ---
def _find_row_by_email(sheet, headers, email: str):
    email_col = _col_index(headers, "Email")
    if not email_col:
        headers = ensure_headers(sheet)
        email_col = _col_index(headers, "Email")
    email_cells = sheet.col_values(email_col)[1:]
    for idx, cell_val in enumerate(email_cells, start=2):
        if (cell_val or "").strip().lower() == email.strip().lower():
            return idx
    return None

def get_subscriber(email: str):
    sheet = open_sheet_with_retry()
    headers = ensure_headers(sheet)
    row_idx = _find_row_by_email(sheet, headers, email)
    if not row_idx:
        return None, None, headers
    values = sheet.row_values(row_idx)
    record = {h: (values[i] if i < len(values) else "") for i, h in enumerate(headers)}
    return record, row_idx, headers

def is_verified(email: str) -> bool:
    rec, _, _ = get_subscriber(email)
    return bool(rec and str(rec.get("Verified", "")).strip().upper() == "TRUE")

def set_pending_subscription(email: str, selected_topics: list, max_items: int, otp_code: str, otp_expires_iso: str):
    sheet = open_sheet_with_retry()
    headers = ensure_headers(sheet)
    now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    row_dict = {
        "Email": email,
        "Technology": "TRUE" if "Technology" in selected_topics else "FALSE",
        "Sports":     "TRUE" if "Sports" in selected_topics else "FALSE",
        "Politics":   "TRUE" if "Politics" in selected_topics else "FALSE",
        "Finance":    "TRUE" if "Finance" in selected_topics else "FALSE",
        "Max_items":  str(max_items),
        "Timestamp":  now_iso,
        "Verified":   "FALSE",
        "OTP_Code":   otp_code,
        "OTP_Expires": otp_expires_iso,
    }
    row_idx = _find_row_by_email(sheet, headers, email)
    if row_idx:
        row_update = [row_dict.get(h, "") for h in headers]
        sheet.update(f"A{row_idx}", [row_update])
        return "updated", row_idx
    else:
        new_row = [row_dict.get(h, "") for h in headers]
        sheet.append_row(new_row)
        return "created", None

def verify_otp(email: str, otp_code: str) -> bool:
    sheet = open_sheet_with_retry()
    headers = ensure_headers(sheet)
    row_idx = _find_row_by_email(sheet, headers, email)
    if not row_idx:
        return False
    values = sheet.row_values(row_idx)
    record = {h: (values[i] if i < len(values) else "") for i, h in enumerate(headers)}
    if (record.get("OTP_Code", "") or "").strip() != (otp_code or "").strip():
        return False
    expires = (record.get("OTP_Expires", "") or "").strip()
    try:
        # Accept both with and without trailing Z
        exp = expires.rstrip("Z")
        from datetime import datetime
        fmt = "%Y-%m-%dT%H:%M:%S"
        if "." in exp:
            fmt = "%Y-%m-%dT%H:%M:%S.%f"
        exp_dt = datetime.fromisoformat(exp)
        if exp_dt < datetime.utcnow():
            return False
    except Exception:
        return False

    # Mark verified and clear OTP
    record["Verified"] = "TRUE"
    record["OTP_Code"] = ""
    record["OTP_Expires"] = ""
    row_update = [record.get(h, "") for h in headers]
    sheet.update(f"A{row_idx}", [row_update])
    return True

def update_preferences(email: str, selected_topics: list, max_items: int = 3):
    sheet = open_sheet_with_retry()
    headers = ensure_headers(sheet)
    row_idx = _find_row_by_email(sheet, headers, email)
    if not row_idx:
        return False
    values = sheet.row_values(row_idx)
    record = {h: (values[i] if i < len(values) else "") for i, h in enumerate(headers)}
    record["Technology"] = "TRUE" if "Technology" in selected_topics else "FALSE"
    record["Sports"] = "TRUE" if "Sports" in selected_topics else "FALSE"
    record["Politics"] = "TRUE" if "Politics" in selected_topics else "FALSE"
    record["Finance"] = "TRUE" if "Finance" in selected_topics else "FALSE"
    record["Max_items"] = str(max_items)
    row_update = [record.get(h, "") for h in headers]
    sheet.update(f"A{row_idx}", [row_update])
    return True

def set_otp(email: str, otp_code: str, otp_expires_iso: str) -> bool:
    """Update or create a row for email with a fresh OTP (keeps existing prefs)."""
    sheet = open_sheet_with_retry()
    headers = ensure_headers(sheet)
    row_idx = _find_row_by_email(sheet, headers, email)
    now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    if row_idx:
        values = sheet.row_values(row_idx)
        record = {h: (values[i] if i < len(values) else "") for i, h in enumerate(headers)}
        record["Verified"] = "FALSE"
        record["OTP_Code"] = otp_code
        record["OTP_Expires"] = otp_expires_iso
        record["Timestamp"] = now_iso
        row_update = [record.get(h, "") for h in headers]
        sheet.update(f"A{row_idx}", [row_update])
        return True
    # If no row, create minimal row
    row_dict = {h: "" for h in headers}
    row_dict["Email"] = email
    row_dict["Verified"] = "FALSE"
    row_dict["OTP_Code"] = otp_code
    row_dict["OTP_Expires"] = otp_expires_iso
    row_dict["Timestamp"] = now_iso
    new_row = [row_dict.get(h, "") for h in headers]
    sheet.append_row(new_row)
    return True

def unsubscribe_user(email):
    """Remove user from the newsletter."""
    try:
        sheet = open_sheet_with_retry()
        headers = ensure_headers(sheet)
        row_idx = _find_row_by_email(sheet, headers, email)
        
        if row_idx:
            # Log the deletion for audit purposes
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Deleting user subscription: {email} (row {row_idx})")
            
            sheet.delete_rows(row_idx)
            return True
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Attempted to delete non-existent user: {email}")
            return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting user {email}: {e}")
        return False

def deactivate_subscription(email):
    """Mark subscription as inactive instead of deleting."""
    try:
        sheet = open_sheet_with_retry()
        headers = ensure_headers(sheet)
        
        # Add "Active" column if it doesn't exist
        if "Active" not in headers:
            headers.append("Active")
            sheet.update("A1", [headers])
            # Refresh headers after adding new column
            headers = ensure_headers(sheet)
        
        row_idx = _find_row_by_email(sheet, headers, email)
        if row_idx:
            active_col = headers.index("Active") + 1
            sheet.update_cell(row_idx, active_col, "FALSE")
            
            # Log the deactivation for audit purposes
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Deactivated subscription for: {email} (row {row_idx})")
            
            return True
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Attempted to deactivate non-existent user: {email}")
            return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deactivating subscription for {email}: {e}")
        return False

def reactivate_subscription(email):
    """Reactivate a deactivated subscription."""
    try:
        sheet = open_sheet_with_retry()
        headers = ensure_headers(sheet)
        
        # Add "Active" column if it doesn't exist
        if "Active" not in headers:
            headers.append("Active")
            sheet.update("A1", [headers])
            # Refresh headers after adding new column
            headers = ensure_headers(sheet)
        
        row_idx = _find_row_by_email(sheet, headers, email)
        if row_idx:
            active_col = headers.index("Active") + 1
            sheet.update_cell(row_idx, active_col, "TRUE")
            
            # Log the reactivation for audit purposes
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Reactivated subscription for: {email} (row {row_idx})")
            
            return True
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Attempted to reactivate non-existent user: {email}")
            return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error reactivating subscription for {email}: {e}")
        return False

def get_all_verified_subscribers():
    """
    Get all verified and active subscribers
    """
    try:
        headers = ensure_headers()
        records = sheet.get_all_records(expected_headers=headers)
        
        verified_subscribers = []
        for record in records:
            # Check if subscriber is verified and active
            if (str(record.get('Verified', '')).upper() == 'TRUE' and 
                str(record.get('Active', 'TRUE')).upper() == 'TRUE' and
                record.get('Email', '').strip()):
                verified_subscribers.append(record)
        
        return verified_subscribers
        
    except Exception as e:
        print(f"❌ Error getting verified subscribers: {e}")
        return []