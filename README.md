# Checkout Metrics Lab

A small payments analytics project: a metrics layer in YAML and SQL, and an A/B test readout for a checkout change. The data is synthetic. `generate_data.py` creates 200,000 checkout sessions across 500 merchants over eight weeks, with charges, declines, refunds, and disputes.

## Question

Does a one-page checkout with saved card details convert more buyers than the current multi-step checkout, without raising refunds or disputes?

## How it works

`metrics.yml` defines each metric once: checkout conversion, payment submit rate, authorization rate, refund rate, dispute rate, and revenue per session. `metrics.py` compiles those definitions into SQL and runs them in DuckDB against `sql/session_facts.sql`, a view with one row per checkout session. Reports ask for metrics by name, so no report re-types a formula.

`ab_test.py` reads the experiment period (weeks 5 to 8) and writes `reports/experiment_readout.md`. It checks for sample ratio mismatch first, then compares control and treatment with two-proportion tests and 95% confidence intervals, checks the refund and dispute guardrails, and splits conversion by device.

## Result (synthetic data)

Checkout conversion rose from 57.84% to 59.67% (+1.83 pp, 95% CI +1.22 to +2.44). The gain came from mobile (+3.05 pp); desktop did not move. Refund rate rose 0.20 pp, but the confidence interval includes zero, so it is a guardrail to keep watching after launch. Full readout: [reports/experiment_readout.md](reports/experiment_readout.md).

## Run it

```bash
pip install -r requirements.txt
python generate_data.py
python metrics.py checkout_conversion authorization_rate --by week
python ab_test.py
```

## Next

- Dashboard of weekly metrics by device and payment method
- Power analysis: how many sessions the test needed
- Refund follow-up: does the one-page checkout raise refunds for some merchant industries?
