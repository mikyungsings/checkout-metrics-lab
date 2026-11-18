# Experiment readout: one-page checkout

Data is synthetic (see generate_data.py). Experiment period: weeks 5-8.

## Sample ratio check

Control sessions: 50,163. Treatment sessions: 50,124. Chi-square p = 0.902 (no mismatch, split is fine).

## Results

| Metric | Control | Treatment | Difference | 95% CI | p-value |
|---|---|---|---|---|---|
| checkout_conversion | 57.84% | 59.67% | +1.83 pp | [+1.22, +2.44] | 0.0000 |
| payment_submit_rate | 62.40% | 64.50% | +2.10 pp | [+1.50, +2.70] | 0.0000 |
| authorization_rate | 92.69% | 92.51% | -0.18 pp | [-0.59, +0.23] | 0.3886 |
| refund_rate (guardrail) | 2.91% | 3.11% | +0.20 pp | [-0.08, +0.47] | 0.1618 |
| dispute_rate (guardrail) | 0.40% | 0.37% | -0.03 pp | [-0.13, +0.07] | 0.5300 |

## Conversion by device

| Metric | Control | Treatment | Difference | 95% CI | p-value |
|---|---|---|---|---|---|
| checkout_conversion, mobile | 54.22% | 57.27% | +3.05 pp | [+2.27, +3.83] | 0.0000 |
| checkout_conversion, desktop | 63.66% | 63.61% | -0.05 pp | [-1.01, +0.92] | 0.9229 |

## Decision

Ship. Conversion rose +1.83 pp and the confidence interval is above zero. Neither guardrail got clearly worse.
