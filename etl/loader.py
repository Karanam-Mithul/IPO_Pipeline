"""
etl/loader.py  - Python 3.8 compatible, no type hints
"""

import logging
import time
import pandas as pd
from datetime import date
from etl.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def upsert_ipo_master(df, conn):
    name_to_id = {}
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(
                """
                INSERT INTO ipo_master
                    (ipo_name, issue_size, offer_price, list_price, current_price,
                     listing_gain, current_gain, open_date, close_date, listing_date,
                     sector, exchange, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                ON CONFLICT (ipo_name) DO UPDATE SET
                    issue_size    = EXCLUDED.issue_size,
                    offer_price   = EXCLUDED.offer_price,
                    list_price    = EXCLUDED.list_price,
                    current_price = EXCLUDED.current_price,
                    listing_gain  = EXCLUDED.listing_gain,
                    current_gain  = EXCLUDED.current_gain,
                    open_date     = EXCLUDED.open_date,
                    close_date    = EXCLUDED.close_date,
                    listing_date  = EXCLUDED.listing_date,
                    sector        = EXCLUDED.sector,
                    exchange      = EXCLUDED.exchange,
                    updated_at    = NOW()
                RETURNING ipo_id
                """,
                (
                    row.get("ipo_name"),
                    row.get("issue_size"),
                    row.get("offer_price"),
                    row.get("list_price"),
                    row.get("current_price"),
                    row.get("listing_gain"),
                    row.get("current_gain"),
                    row.get("open_date") or None,
                    row.get("close_date") or None,
                    row.get("listing_date") or None,
                    row.get("sector"),
                    row.get("exchange", "NSE"),
                ),
            )
            ipo_id = cur.fetchone()[0]
            name_to_id[row["ipo_name"]] = ipo_id
    return name_to_id


def insert_subscription(df, name_to_id, conn):
    sub_cols = ["qib", "hni", "rii", "total_subscription"]
    has_sub = any(df[col].notna().any() for col in sub_cols if col in df.columns)
    if not has_sub:
        logger.info("No subscription data found; skipping.")
        return
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            ipo_id = name_to_id.get(row["ipo_name"])
            if ipo_id is None:
                continue
            cur.execute(
                "INSERT INTO ipo_subscription (ipo_id, qib, hni, rii, total_subscription) VALUES (%s,%s,%s,%s,%s)",
                (ipo_id, row.get("qib"), row.get("hni"), row.get("rii"), row.get("total_subscription")),
            )


def log_pipeline_run(stage, status, records_in, records_out, duration_sec, error_msg, conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_log (run_date, stage, status, records_in, records_out, error_msg, duration_sec) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (date.today(), stage, status, records_in, records_out, error_msg, round(duration_sec, 2)),
        )


def run_load(df):
    logger.info("=== Loader Started: %d records ===", len(df))
    t0 = time.time()
    conn = get_connection()
    try:
        name_to_id = upsert_ipo_master(df, conn)
        insert_subscription(df, name_to_id, conn)
        duration = time.time() - t0
        log_pipeline_run("load", "success", len(df), len(name_to_id), duration, None, conn)
        conn.commit()
        logger.info("=== Loader Completed: %d records upserted in %.1fs ===", len(name_to_id), duration)
    except Exception as exc:
        conn.rollback()
        log_pipeline_run("load", "failed", len(df), 0, time.time() - t0, str(exc), conn)
        conn.commit()
        logger.error("Load failed: %s", exc)
        raise
    finally:
        conn.close()
