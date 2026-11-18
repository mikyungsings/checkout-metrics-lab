"""Generate a synthetic payments dataset for the checkout experiment.

All data is made up. It is shaped like an online payments business:
merchants, checkout sessions, charges, refunds and disputes.

Weeks 1-4 are a pre-period. In weeks 5-8 a 50/50 experiment runs:
  control   = current multi-step checkout
  treatment = one-page checkout with saved card details

Usage: python generate_data.py [--sessions 200000] [--seed 7]
Writes Parquet files to data/.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

COUNTRIES = ["US", "GB", "DE", "JP", "KR", "BR"]
COUNTRY_P = [0.45, 0.15, 0.12, 0.10, 0.08, 0.10]
METHODS = ["card", "wallet", "bank_debit"]
METHOD_P = [0.70, 0.22, 0.08]
DEVICES = ["mobile", "desktop"]
DEVICE_P = [0.62, 0.38]
START = pd.Timestamp("2026-09-07")
EXPERIMENT_START = START + pd.Timedelta(weeks=4)


def build(n_sessions: int, seed: int) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    # Merchants
    n_merchants = 500
    merchants = pd.DataFrame({
        "merchant_id": [f"m_{i:04d}" for i in range(n_merchants)],
        "industry": rng.choice(["retail", "saas", "travel", "food", "digital_goods"],
                               n_merchants, p=[0.35, 0.2, 0.1, 0.15, 0.2]),
        "signup_date": START - pd.to_timedelta(rng.integers(30, 900, n_merchants), unit="D"),
    })
    # A few large merchants carry most of the volume
    merchant_weight = rng.pareto(1.5, n_merchants) + 1
    merchant_weight /= merchant_weight.sum()

    # Checkout sessions
    ts = START + pd.to_timedelta(rng.uniform(0, 8 * 7 * 24 * 3600, n_sessions), unit="s")
    sessions = pd.DataFrame({
        "session_id": [f"s_{i:07d}" for i in range(n_sessions)],
        "merchant_id": rng.choice(merchants.merchant_id, n_sessions, p=merchant_weight),
        "started_at": ts,
        "country": rng.choice(COUNTRIES, n_sessions, p=COUNTRY_P),
        "device": rng.choice(DEVICES, n_sessions, p=DEVICE_P),
        "payment_method": rng.choice(METHODS, n_sessions, p=METHOD_P),
    })
    in_exp = sessions.started_at >= EXPERIMENT_START
    sessions["variant"] = np.where(in_exp, rng.choice(["control", "treatment"], n_sessions), None)

    # Did the buyer submit payment? Base rate varies by device;
    # treatment lifts mobile more than desktop.
    p_submit = np.where(sessions.device == "mobile", 0.58, 0.68)
    lift = np.where(sessions.device == "mobile", 0.035, 0.010)
    p_submit = p_submit + np.where(sessions.variant == "treatment", lift, 0.0)
    submitted = rng.random(n_sessions) < p_submit
    sessions["submitted_payment"] = submitted

    # Charges for submitted sessions
    ch = sessions[submitted].copy()
    n_ch = len(ch)
    amount = np.round(np.exp(rng.normal(3.7, 0.9, n_ch)), 2)  # USD, median about 40
    p_decline = np.select(
        [ch.payment_method == "card", ch.payment_method == "wallet"], [0.08, 0.04], 0.11)
    status = np.where(rng.random(n_ch) < p_decline, "declined", "succeeded")
    charges = pd.DataFrame({
        "charge_id": [f"ch_{i:07d}" for i in range(n_ch)],
        "session_id": ch.session_id.values,
        "merchant_id": ch.merchant_id.values,
        "created_at": ch.started_at.values + pd.to_timedelta(rng.integers(20, 600, n_ch), unit="s"),
        "amount_usd": amount,
        "status": status,
    })

    ok = charges[charges.status == "succeeded"]
    # Refunds: treatment has a slightly higher rate (a guardrail to check)
    variant_of = sessions.set_index("session_id").variant
    ok_variant = variant_of.reindex(ok.session_id).values
    p_refund = np.where(ok_variant == "treatment", 0.032, 0.030)
    refunded = rng.random(len(ok)) < p_refund
    refunds = pd.DataFrame({
        "refund_id": [f"re_{i:06d}" for i in range(refunded.sum())],
        "charge_id": ok.charge_id.values[refunded],
        "created_at": ok.created_at.values[refunded]
        + pd.to_timedelta(rng.integers(1, 30, refunded.sum()), unit="D"),
        "amount_usd": ok.amount_usd.values[refunded],
    })

    disputed = rng.random(len(ok)) < 0.004
    disputes = pd.DataFrame({
        "dispute_id": [f"dp_{i:05d}" for i in range(disputed.sum())],
        "charge_id": ok.charge_id.values[disputed],
        "created_at": ok.created_at.values[disputed]
        + pd.to_timedelta(rng.integers(5, 60, disputed.sum()), unit="D"),
        "reason": rng.choice(["fraudulent", "product_not_received", "duplicate"],
                             disputed.sum(), p=[0.6, 0.3, 0.1]),
    })

    return {"merchants": merchants, "sessions": sessions, "charges": charges,
            "refunds": refunds, "disputes": disputes}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    out = Path(__file__).parent / "data"
    out.mkdir(exist_ok=True)
    for name, df in build(args.sessions, args.seed).items():
        df.to_parquet(out / f"{name}.parquet", index=False)
        print(f"{name:10s} {len(df):>8,d} rows")


if __name__ == "__main__":
    main()
