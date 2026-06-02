"""
etl/transformer.py  - Python 3.8 compatible, no type hints
"""

import os
import logging
import pandas as pd
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_DATA_PATH = os.getenv("PROCESSED_DATA_PATH", "/opt/airflow/data/processed")
DATE_FORMATS = ["%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d", "%b %d, %Y", "%d %b %Y"]


def parse_date(value):
    if not value or str(value).strip() in ["-", "N/A", "nan", ""]:
        return None
    for fmt in DATE_FORMATS:
        try:
            return pd.to_datetime(str(value).strip(), format=fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(str(value).strip(), infer_datetime_format=True)
    except Exception:
        return None


def normalize_dates(df):
    for col in ["open_date", "close_date", "listing_date"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_date)
    return df


def calculate_listing_gain(df):
    mask = df["list_price"].notna() & df["offer_price"].notna() & (df["offer_price"] != 0)
    df.loc[mask, "listing_gain"] = (
        (df.loc[mask, "list_price"] - df.loc[mask, "offer_price"])
        / df.loc[mask, "offer_price"] * 100
    ).round(2)
    return df


def calculate_current_gain(df):
    mask = df["current_price"].notna() & df["offer_price"].notna() & (df["offer_price"] != 0)
    df.loc[mask, "current_gain"] = (
        (df.loc[mask, "current_price"] - df.loc[mask, "offer_price"])
        / df.loc[mask, "offer_price"] * 100
    ).round(2)
    return df


def standardize_columns(df):
    expected_cols = [
        "ipo_name", "open_date", "close_date", "listing_date",
        "issue_size", "offer_price", "list_price", "current_price",
        "listing_gain", "current_gain",
        "qib", "hni", "rii", "total_subscription",
        "sector", "exchange",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
    for col in ["ipo_name", "sector", "exchange"]:
        df[col] = df[col].astype(str).str.strip().replace("nan", None)
    df["exchange"] = df["exchange"].fillna("NSE")
    return df[expected_cols]


def save_processed(df):
    os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(PROCESSED_DATA_PATH, "ipo_processed_%s.csv" % timestamp)
    df.to_csv(filepath, index=False)
    logger.info("Processed data saved -> %s  (%d records)", filepath, len(df))
    return filepath


def run_transformation(df):
    logger.info("=== Transformation Started ===")
    df = normalize_dates(df)
    df = standardize_columns(df)
    df = calculate_listing_gain(df)
    df = calculate_current_gain(df)
    filepath = save_processed(df)
    logger.info("=== Transformation Completed ===")
    return df, filepath
