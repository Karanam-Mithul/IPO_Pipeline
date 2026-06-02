"""
etl/kpi_generator.py
Generates and logs KPI summaries from ipo_master into pipeline_log.
"""

import logging
from etl.db import get_connection

logger = logging.getLogger(__name__)


def generate_and_log_kpis():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*)                            AS total_ipos,
                    ROUND(SUM(issue_size)::numeric, 2)  AS total_funds_cr,
                    ROUND(AVG(listing_gain)::numeric, 2) AS avg_listing_gain,
                    ROUND(MAX(listing_gain)::numeric, 2) AS max_listing_gain,
                    ROUND(MIN(listing_gain)::numeric, 2) AS min_listing_gain
                FROM ipo_master
                WHERE listing_gain IS NOT NULL
            """)
            row = cur.fetchone()
            kpis = {
                "total_ipos":        row[0],
                "total_funds_cr":    float(row[1] or 0),
                "avg_listing_gain":  float(row[2] or 0),
                "max_listing_gain":  float(row[3] or 0),
                "min_listing_gain":  float(row[4] or 0),
            }
            logger.info(f"KPIs: {kpis}")
        conn.commit()
        return kpis
    finally:
        conn.close()
