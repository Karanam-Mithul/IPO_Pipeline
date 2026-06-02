"""
etl/validator.py  - Python 3.8 compatible, no type hints
"""

import logging
import pandas as pd
from datetime import date
from etl.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ValidationError:
    def __init__(self, ipo_name, error_type, detail):
        self.ipo_name = ipo_name
        self.error_type = error_type
        self.detail = detail


def validate(df):
    errors = []
    invalid_indices = set()

    missing_name = df[df["ipo_name"].isna() | (df["ipo_name"].astype(str).str.strip() == "")]
    for idx in missing_name.index:
        errors.append(ValidationError("UNKNOWN", "missing_name", "Row %d has no IPO name" % idx))
        invalid_indices.add(idx)

    missing_price = df[df["offer_price"].isna()]
    for idx in missing_price.index:
        errors.append(ValidationError(df.at[idx, "ipo_name"], "missing_offer_price", "offer_price is NULL"))
        invalid_indices.add(idx)

    for col in ["offer_price", "list_price", "current_price"]:
        bad = df[df[col].notna() & (df[col] <= 0)]
        for idx in bad.index:
            errors.append(ValidationError(df.at[idx, "ipo_name"], "non_positive_%s" % col, "%s = %s" % (col, df.at[idx, col])))
            invalid_indices.add(idx)

    bad_size = df[df["issue_size"].notna() & (df["issue_size"] <= 0)]
    for idx in bad_size.index:
        errors.append(ValidationError(df.at[idx, "ipo_name"], "non_positive_issue_size", "issue_size = %s" % df.at[idx, "issue_size"]))
        invalid_indices.add(idx)

    dupes = df[df.duplicated(subset=["ipo_name"], keep="first")]
    for idx in dupes.index:
        errors.append(ValidationError(df.at[idx, "ipo_name"], "duplicate_record", "Duplicate ipo_name"))
        invalid_indices.add(idx)

    df_dates = df.copy()
    for col in ["open_date", "close_date"]:
        df_dates[col] = pd.to_datetime(df_dates[col], errors="coerce")
    bad_dates = df_dates[
        df_dates["open_date"].notna()
        & df_dates["close_date"].notna()
        & (df_dates["close_date"] < df_dates["open_date"])
    ]
    for idx in bad_dates.index:
        errors.append(ValidationError(df.at[idx, "ipo_name"], "invalid_date_range", "close_date < open_date"))
        invalid_indices.add(idx)

    clean_df = df.drop(index=list(invalid_indices)).reset_index(drop=True)
    logger.info("Validation: %d in -> %d valid, %d errors", len(df), len(clean_df), len(errors))
    return clean_df, errors


def log_errors_to_db(errors, run_date=None):
    if not errors:
        return
    run_date = run_date or date.today()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for err in errors:
                cur.execute(
                    "INSERT INTO validation_errors (run_date, ipo_name, error_type, error_detail) VALUES (%s,%s,%s,%s)",
                    (run_date, err.ipo_name, err.error_type, err.detail),
                )
        conn.commit()
        logger.info("Logged %d validation errors to DB.", len(errors))
    finally:
        conn.close()


def run_validation(df):
    clean_df, errors = validate(df)
    log_errors_to_db(errors)
    return clean_df
