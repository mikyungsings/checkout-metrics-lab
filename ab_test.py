"""Experiment readout: one-page checkout (treatment) vs current checkout (control).

Checks, in order:
  1. Sample ratio mismatch (was traffic really split 50/50?)
  2. Primary metric: checkout_conversion, with a 95% confidence interval
  3. Guardrails: refund_rate and dispute_rate must not get worse
  4. Segments: mobile vs desktop

Writes reports/experiment_readout.md
"""
from pathlib import Path

import numpy as np
from scipy import stats

from metrics import connect, load_metrics, query_metrics

ROOT = Path(__file__).parent
ALPHA = 0.05


def two_prop(n1, x1, n2, x2):
    """Difference treatment minus control, normal-approximation CI and p-value."""
    p1, p2 = x1 / n1, x2 / n2
    diff = p2 - p1
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    pooled = (x1 + x2) / (n1 + n2)
    se0 = np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = diff / se0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    z_crit = stats.norm.ppf(1 - ALPHA / 2)
    return p1, p2, diff, (diff - z_crit * se, diff + z_crit * se), p


def compare(df, metric):
    c = df[df.variant == "control"].iloc[0]
    t = df[df.variant == "treatment"].iloc[0]
    return two_prop(c[f"{metric}__den"], c[f"{metric}__num"], t[f"{metric}__den"], t[f"{metric}__num"])


def fmt_row(name, r):
    p1, p2, diff, (lo, hi), p = r
    return (f"| {name} | {p1:.2%} | {p2:.2%} | {diff * 100:+.2f} pp "
            f"| [{lo * 100:+.2f}, {hi * 100:+.2f}] | {p:.4f} |")


def main() -> None:
    con = connect()
    defs = load_metrics()
    names = ["checkout_conversion", "payment_submit_rate", "authorization_rate",
             "refund_rate", "dispute_rate"]
    exp = "variant is not null"
    overall = query_metrics(con, names, by=["variant"], where=exp)
    seg = query_metrics(con, ["checkout_conversion"], by=["device", "variant"], where=exp)

    # 1. Sample ratio mismatch
    counts = overall.set_index("variant")["checkout_conversion__den"]
    chi2, srm_p = stats.chisquare(counts.values)

    header = ("| Metric | Control | Treatment | Difference | 95% CI | p-value |\n"
              "|---|---|---|---|---|---|")
    lines = ["# Experiment readout: one-page checkout", "",
             "Data is synthetic (see generate_data.py). Experiment period: weeks 5-8.", "",
             "## Sample ratio check", "",
             f"Control sessions: {int(counts['control']):,}. Treatment sessions: {int(counts['treatment']):,}. "
             f"Chi-square p = {srm_p:.3f} "
             + ("(no mismatch, split is fine)." if srm_p > 0.01 else "(MISMATCH, do not trust results)."),
             "", "## Results", "", header]

    results = {}
    for m in names:
        results[m] = compare(overall, m)
        label = m + (" (guardrail)" if defs[m].get("guardrail") else "")
        lines.append(fmt_row(label, results[m]))

    lines += ["", "## Conversion by device", "", header]
    for dev in ["mobile", "desktop"]:
        lines.append(fmt_row(f"checkout_conversion, {dev}", compare(seg[seg.device == dev], "checkout_conversion")))

    # Decision
    prim = results["checkout_conversion"]
    prim_win = prim[3][0] > 0
    bad_guard = [g for g in ["refund_rate", "dispute_rate"]
                 if results[g][3][0] > 0]  # CI entirely above zero = clearly worse
    lines += ["", "## Decision", ""]
    if prim_win and not bad_guard:
        lines.append(f"Ship. Conversion rose {prim[2] * 100:+.2f} pp and the confidence interval "
                     "is above zero. Neither guardrail got clearly worse.")
    elif prim_win:
        lines.append(f"Hold. Conversion rose {prim[2] * 100:+.2f} pp, but {', '.join(bad_guard)} got worse. "
                     "Review the guardrail before shipping.")
    else:
        lines.append("Do not ship yet. The conversion change is not distinguishable from zero.")

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "experiment_readout.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
