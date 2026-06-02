"""
tests/test_etl.py
Unit tests for the validator and transformer modules.
Run with: pytest tests/
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pandas as pd
from etl.validator import validate
from etl.transformer import (
    normalize_dates, calculate_listing_gain,
    calculate_current_gain, standardize_columns,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────
def make_df(**overrides) -> pd.DataFrame:
    base = {
        "ipo_name":     ["Test IPO"],
        "open_date":    ["15-Jan-2024"],
        "close_date":   ["17-Jan-2024"],
        "listing_date": ["22-Jan-2024"],
        "issue_size":   [500.0],
        "offer_price":  [100.0],
        "list_price":   [150.0],
        "current_price":[160.0],
        "listing_gain": [None],
        "current_gain": [None],
        "qib":          [50.0],
        "hni":          [30.0],
        "rii":          [20.0],
        "total_subscription": [40.0],
        "sector":       ["Technology"],
        "exchange":     ["NSE"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


# ─── Validator tests ──────────────────────────────────────────────────────────
class TestValidator:

    def test_valid_record_passes(self):
        df = make_df()
        clean, errors = validate(df)
        assert len(clean) == 1
        assert len(errors) == 0

    def test_missing_ipo_name_flagged(self):
        df = make_df(ipo_name=[""])
        clean, errors = validate(df)
        assert len(clean) == 0
        assert any(e.error_type == "missing_name" for e in errors)

    def test_missing_offer_price_flagged(self):
        df = make_df(offer_price=[None])
        clean, errors = validate(df)
        assert len(clean) == 0
        assert any(e.error_type == "missing_offer_price" for e in errors)

    def test_negative_offer_price_flagged(self):
        df = make_df(offer_price=[-50.0])
        clean, errors = validate(df)
        assert any("non_positive_offer_price" in e.error_type for e in errors)

    def test_duplicate_records_flagged(self):
        df = pd.concat([make_df(), make_df()], ignore_index=True)
        clean, errors = validate(df)
        assert len(clean) == 1
        assert any(e.error_type == "duplicate_record" for e in errors)

    def test_invalid_date_range_flagged(self):
        df = make_df(open_date=["20-Jan-2024"], close_date=["15-Jan-2024"])
        clean, errors = validate(df)
        assert any(e.error_type == "invalid_date_range" for e in errors)

    def test_multiple_valid_records_all_pass(self):
        rows = {k: [v[0]] * 5 for k, v in make_df().to_dict(orient="list").items()}
        # Give unique names
        rows["ipo_name"] = [f"IPO {i}" for i in range(5)]
        df = pd.DataFrame(rows)
        clean, errors = validate(df)
        assert len(clean) == 5
        assert len(errors) == 0


# ─── Transformer tests ────────────────────────────────────────────────────────
class TestTransformer:

    def test_listing_gain_calculated(self):
        df = make_df(offer_price=[100.0], list_price=[150.0])
        df = calculate_listing_gain(df)
        assert df.loc[0, "listing_gain"] == pytest.approx(50.0)

    def test_current_gain_calculated(self):
        df = make_df(offer_price=[100.0], current_price=[80.0])
        df = calculate_current_gain(df)
        assert df.loc[0, "current_gain"] == pytest.approx(-20.0)

    def test_zero_offer_price_skipped(self):
        df = make_df(offer_price=[0.0], list_price=[100.0])
        df = calculate_listing_gain(df)
        assert pd.isna(df.loc[0, "listing_gain"])

    def test_missing_list_price_skipped(self):
        df = make_df(offer_price=[100.0], list_price=[None])
        df = calculate_listing_gain(df)
        assert pd.isna(df.loc[0, "listing_gain"])

    def test_date_normalization(self):
        df = make_df(open_date=["15-Jan-2024"])
        df = normalize_dates(df)
        assert pd.notna(df.loc[0, "open_date"])
        assert df.loc[0, "open_date"].year == 2024

    def test_standardize_adds_missing_cols(self):
        df = pd.DataFrame({"ipo_name": ["X"], "offer_price": [100.0]})
        df = standardize_columns(df)
        assert "sector" in df.columns
        assert "exchange" in df.columns

    def test_exchange_defaults_to_nse(self):
        df = make_df(exchange=[None])
        df = standardize_columns(df)
        assert df.loc[0, "exchange"] == "NSE"
