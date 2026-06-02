"""
dags/ipo_pipeline_dag.py
Airflow DAG: ipo_data_pipeline
Runs daily at 18:30 IST (13:00 UTC) — after Indian market close.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator

# ── Default args ──────────────────────────────────────────────────────────────
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email": [os.getenv("ALERT_EMAIL", "admin@ipo.com")],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# ── DAG definition ────────────────────────────────────────────────────────────
with DAG(
    dag_id="ipo_data_pipeline",
    default_args=default_args,
    description="End-to-end IPO data pipeline: scrape → validate → transform → load",
    schedule_interval="0 13 * * 1-5",   # Mon–Fri 13:00 UTC (18:30 IST)
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["ipo", "etl", "production"],
    max_active_runs=1,
) as dag:

    # ── Task 1: Scrape ────────────────────────────────────────────────────────
    def task_scrape(**context):
        from scraper.ipo_scraper import run_scraper
        filepath = run_scraper()
        # Push filepath to XCom so downstream tasks can read it
        context["ti"].xcom_push(key="raw_filepath", value=filepath)
        logging.info(f"Scrape complete → {filepath}")

    scrape = PythonOperator(
        task_id="scrape_ipo_data",
        python_callable=task_scrape,
    )

    # ── Task 2: Validate ──────────────────────────────────────────────────────
    def task_validate(**context):
        from etl.validator import run_validation
        raw_filepath = context["ti"].xcom_pull(task_ids="scrape_ipo_data", key="raw_filepath")
        df = pd.read_csv(raw_filepath)
        logging.info(f"Validating {len(df)} raw records from {raw_filepath}")
        clean_df = run_validation(df)
        # Store clean df path via XCom
        import tempfile, pickle, os
        tmp = os.path.join("/opt/airflow/data/raw", "validated_tmp.pkl")
        clean_df.to_pickle(tmp)
        context["ti"].xcom_push(key="validated_pkl", value=tmp)

    validate = PythonOperator(
        task_id="validate_data",
        python_callable=task_validate,
    )

    # ── Task 3: Transform ─────────────────────────────────────────────────────
    def task_transform(**context):
        from etl.transformer import run_transformation
        pkl_path = context["ti"].xcom_pull(task_ids="validate_data", key="validated_pkl")
        df = pd.read_pickle(pkl_path)
        transformed_df, processed_path = run_transformation(df)
        tmp = "/opt/airflow/data/processed/transformed_tmp.pkl"
        transformed_df.to_pickle(tmp)
        context["ti"].xcom_push(key="transformed_pkl", value=tmp)
        context["ti"].xcom_push(key="processed_filepath", value=processed_path)

    transform = PythonOperator(
        task_id="transform_data",
        python_callable=task_transform,
    )

    # ── Task 4: Load ──────────────────────────────────────────────────────────
    def task_load(**context):
        from etl.loader import run_load
        pkl_path = context["ti"].xcom_pull(task_ids="transform_data", key="transformed_pkl")
        df = pd.read_pickle(pkl_path)
        run_load(df)

    load = PythonOperator(
        task_id="load_postgres",
        python_callable=task_load,
    )

    # ── Task 5: Generate KPIs ─────────────────────────────────────────────────
    def task_generate_kpis(**context):
        from etl.db import get_connection
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*)                        AS total_ipos,
                        ROUND(SUM(issue_size), 2)       AS total_funds_cr,
                        ROUND(AVG(listing_gain), 2)     AS avg_listing_gain_pct,
                        ROUND(MAX(listing_gain), 2)     AS max_listing_gain_pct,
                        ROUND(MIN(listing_gain), 2)     AS min_listing_gain_pct
                    FROM ipo_master
                    WHERE listing_gain IS NOT NULL
                """)
                row = cur.fetchone()
                logging.info(
                    f"KPIs → Total IPOs: {row[0]}, Funds: ₹{row[1]} Cr, "
                    f"Avg Gain: {row[2]}%, Max: {row[3]}%, Min: {row[4]}%"
                )
                context["ti"].xcom_push(key="kpis", value={
                    "total_ipos": row[0],
                    "total_funds_cr": float(row[1] or 0),
                    "avg_listing_gain": float(row[2] or 0),
                })
        finally:
            conn.close()

    generate_kpis = PythonOperator(
        task_id="generate_kpis",
        python_callable=task_generate_kpis,
    )

    # ── Task 6: Notify ────────────────────────────────────────────────────────
    def task_notify(**context):
        kpis = context["ti"].xcom_pull(task_ids="generate_kpis", key="kpis") or {}
        logging.info(
            f"Pipeline SUCCESS — "
            f"Total IPOs: {kpis.get('total_ipos', 'N/A')}, "
            f"Avg Listing Gain: {kpis.get('avg_listing_gain', 'N/A')}%"
        )

    notify = PythonOperator(
        task_id="send_notification",
        python_callable=task_notify,
    )

    # ── Task Dependencies ─────────────────────────────────────────────────────
    scrape >> validate >> transform >> load >> generate_kpis >> notify
