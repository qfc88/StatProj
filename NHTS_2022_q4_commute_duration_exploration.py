"""Focused exploratory analysis for NHTS 2022 Question 4: commute duration.

Research direction
------------------
For adult weekday home-based work trips, how accurately can information that is
available before (or at the start of) a trip predict reported trip duration?

This script is deliberately exploratory. It does not fit or select a final
prediction model. It:

* verifies the analysis population and identifiers;
* profiles duration, missingness, weights, and extreme values;
* measures duration relationships using Spearman correlation, weighted
  Spearman correlation, and rank eta;
* uses bias-corrected Cramer's V to diagnose overlap among categorical
  predictors;
* checks numerical predictor redundancy;
* compares results by mode, direction, departure period, and geography; and
* writes a proposal-oriented Markdown and HTML report.

Source files are read only. All generated files are written to
``q4_commute_duration_exploration``.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import html
import json
import math
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import chi2_contingency, rankdata


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "nhts_weekday_commute_analysis.csv"
RAW_TRIPS = ROOT / "Data" / "tripv2pub.csv"
OUT = ROOT / "q4_commute_duration_exploration"
SPECIAL_CODES = {-1, -7, -8, -9}
RNG_SEED = 20221017
BOOTSTRAP_REPS = 400


@dataclass(frozen=True)
class VariableSpec:
    name: str
    label: str
    role: str
    kind: str


VARIABLES = [
    VariableSpec("TRVLCMIN", "Reported trip duration (minutes)", "outcome", "numeric"),
    VariableSpec("GCDWORK", "Great-circle home-work distance (miles)", "candidate", "numeric"),
    VariableSpec("R_AGE", "Respondent age", "candidate", "numeric"),
    VariableSpec("HHFAMINC_IMP", "Household income band (imputed)", "candidate", "ordered"),
    VariableSpec("HHVEHCNT", "Household vehicle count", "candidate", "numeric"),
    VariableSpec("HBPPOPDN", "Home block-group population-density band", "density alternative", "ordered"),
    VariableSpec("HBRESDN", "Home block-group residential-density band", "density alternative", "ordered"),
    VariableSpec("HTRESDN", "Home census-tract residential-density band", "density alternative", "ordered"),
    VariableSpec("TRPMILES", "Realised trip miles", "leakage diagnostic", "numeric"),
    VariableSpec("mode_3cat", "Trip mode: car, public transport, active travel", "candidate if mode is known", "categorical"),
    VariableSpec("trip_direction", "Home-to-work, work-to-home, or other HBW", "candidate", "categorical"),
    VariableSpec("departure_period", "Departure-time period", "candidate", "categorical"),
    VariableSpec("TRAVDAY", "Travel day of week", "candidate", "categorical"),
    VariableSpec("RAIL", "Household MSA heavy-rail status", "candidate", "categorical"),
    VariableSpec("URBRUR", "Household urban/rural status", "candidate", "categorical"),
    VariableSpec("MSACAT", "Metropolitan-area category", "candidate alternative", "categorical"),
    VariableSpec("HOMEOWN", "Housing tenure", "candidate", "categorical"),
    VariableSpec("R_SEX_IMP", "Respondent sex (imputed)", "candidate", "categorical"),
]

NUMERIC_FIELDS = [s.name for s in VARIABLES if s.kind in {"numeric", "ordered"}]
CATEGORICAL_FIELDS = [s.name for s in VARIABLES if s.kind == "categorical"]
LABELS = {s.name: s.label for s in VARIABLES}
ROLES = {s.name: s.role for s in VARIABLES}


def clean_special_codes(frame: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for field in fields:
        if field in result.columns and pd.api.types.is_numeric_dtype(result[field]):
            result[field] = result[field].mask(result[field].isin(SPECIAL_CODES))
    return result


def weighted_quantile(values, weights, quantile: float) -> float:
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not valid.any():
        return np.nan
    values = values[valid]
    weights = weights[valid]
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cumulative = np.cumsum(weights) - 0.5 * weights
    cumulative /= weights.sum()
    return float(np.interp(quantile, cumulative, values))


def weighted_pearson(x, y, weights) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    weights = np.asarray(weights, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if valid.sum() < 3:
        return np.nan
    x, y, weights = x[valid], y[valid], weights[valid]
    weights = weights / weights.sum()
    x_centered = x - np.sum(weights * x)
    y_centered = y - np.sum(weights * y)
    denominator = math.sqrt(np.sum(weights * x_centered**2) * np.sum(weights * y_centered**2))
    return float(np.sum(weights * x_centered * y_centered) / denominator) if denominator else np.nan


def weighted_spearman(x, y, weights) -> float:
    pair = pd.DataFrame({"x": x, "y": y, "w": weights}).dropna()
    pair = pair.loc[pair.w > 0]
    if len(pair) < 3 or pair.x.nunique() < 2 or pair.y.nunique() < 2:
        return np.nan
    return weighted_pearson(rankdata(pair.x), rankdata(pair.y), pair.w)


def rank_eta(category, numeric) -> tuple[float, int]:
    data = pd.DataFrame({"category": category, "numeric": numeric}).dropna()
    if len(data) < 2 or data.category.nunique() < 2 or data.numeric.nunique() < 2:
        return np.nan, len(data)
    data["rank"] = rankdata(data.numeric)
    overall = data["rank"].mean()
    total = ((data["rank"] - overall) ** 2).sum()
    between = sum(
        len(group) * (group["rank"].mean() - overall) ** 2
        for _, group in data.groupby("category", observed=True)
    )
    return (float(math.sqrt(between / total)) if total > 0 else np.nan), len(data)


def bias_corrected_cramers_v(x, y) -> tuple[float, int, int, int]:
    data = pd.DataFrame({"x": x, "y": y}).dropna()
    table = pd.crosstab(data.x, data.y)
    n = int(table.to_numpy().sum())
    rows, columns = table.shape
    if n <= 1 or rows <= 1 or columns <= 1:
        return np.nan, n, rows, columns
    chi2 = chi2_contingency(table, correction=False)[0]
    phi2_corrected = max(0.0, chi2 / n - ((columns - 1) * (rows - 1)) / (n - 1))
    rows_corrected = rows - (rows - 1) ** 2 / (n - 1)
    columns_corrected = columns - (columns - 1) ** 2 / (n - 1)
    denominator = min(rows_corrected - 1, columns_corrected - 1)
    value = math.sqrt(phi2_corrected / denominator) if denominator > 0 else np.nan
    return float(value), n, rows, columns


def cluster_bootstrap_spearman(
    data: pd.DataFrame,
    predictor: str,
    outcome: str = "TRVLCMIN",
    cluster: str = "HOUSEID",
    repetitions: int = BOOTSTRAP_REPS,
) -> tuple[float, float]:
    pair = data[[cluster, predictor, outcome]].dropna()
    cluster_codes, clusters = pd.factorize(pair[cluster], sort=False)
    cluster_count = len(clusters)
    if cluster_count < 20 or pair[predictor].nunique() < 2:
        return np.nan, np.nan
    x = pair[predictor].to_numpy(dtype=float)
    y = pair[outcome].to_numpy(dtype=float)
    _, x_groups = np.unique(x, return_inverse=True)
    _, y_groups = np.unique(y, return_inverse=True)
    rng = np.random.default_rng(RNG_SEED + sum(ord(c) for c in predictor))
    estimates = []
    for _ in range(repetitions):
        sampled_cluster_counts = rng.multinomial(
            cluster_count,
            np.full(cluster_count, 1.0 / cluster_count),
        )
        row_weights = sampled_cluster_counts[cluster_codes].astype(float)

        # Exact midranks for the expanded bootstrap sample, calculated without
        # physically repeating rows. Each household's sampled frequency is the
        # frequency of every one of its trip rows in that bootstrap replicate.
        x_frequency = np.bincount(x_groups, weights=row_weights)
        y_frequency = np.bincount(y_groups, weights=row_weights)
        x_ranks_by_group = np.cumsum(x_frequency) - x_frequency + (x_frequency + 1) / 2
        y_ranks_by_group = np.cumsum(y_frequency) - y_frequency + (y_frequency + 1) / 2
        estimate = weighted_pearson(
            x_ranks_by_group[x_groups],
            y_ranks_by_group[y_groups],
            row_weights,
        )
        if np.isfinite(estimate):
            estimates.append(estimate)
    if len(estimates) < repetitions * 0.8:
        return np.nan, np.nan
    return tuple(np.quantile(estimates, [0.025, 0.975]))


def derive_fields(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result["trip_direction"] = np.select(
        [
            result.WHYFROM.eq(1) & result.WHYTO.eq(3),
            result.WHYFROM.eq(3) & result.WHYTO.eq(1),
        ],
        ["home_to_work", "work_to_home"],
        default="other_home_based_work",
    )

    start = pd.to_numeric(result.STRTTIME, errors="coerce")
    start = start.mask(start.isin(SPECIAL_CODES))
    hours = np.floor(start / 100)
    minutes = start % 100
    valid_time = hours.between(0, 23) & minutes.between(0, 59)
    result["departure_minute"] = np.where(valid_time, hours * 60 + minutes, np.nan)
    result["departure_period"] = pd.cut(
        result["departure_minute"],
        bins=[-1, 359, 539, 959, 1139, 1439],
        labels=["overnight_00_05", "am_peak_06_08", "midday_09_15", "pm_peak_16_18", "evening_19_23"],
    ).astype("object")
    day_labels = {2: "Monday", 3: "Tuesday", 4: "Wednesday", 5: "Thursday", 6: "Friday"}
    result["travel_day_label"] = result.TRAVDAY.map(day_labels)
    return result


def summarise_group(data: pd.DataFrame, field: str) -> pd.DataFrame:
    rows = []
    for value, group in data.groupby(field, observed=True, dropna=False):
        valid = group.loc[group.TRVLCMIN.notna() & group.WTTRDFIN5D.gt(0)]
        if valid.empty:
            continue
        rows.append(
            {
                "group": "Missing" if pd.isna(value) else str(value),
                "raw_n": len(valid),
                "people_n": valid[["HOUSEID", "PERSONID"]].drop_duplicates().shape[0],
                "weighted_share_pct": 100 * valid.WTTRDFIN5D.sum() / data.loc[data.TRVLCMIN.notna(), "WTTRDFIN5D"].sum(),
                "mean_minutes": valid.TRVLCMIN.mean(),
                "median_minutes": valid.TRVLCMIN.median(),
                "p90_minutes": valid.TRVLCMIN.quantile(0.90),
                "weighted_median_minutes": weighted_quantile(valid.TRVLCMIN, valid.WTTRDFIN5D, 0.50),
                "weighted_p90_minutes": weighted_quantile(valid.TRVLCMIN, valid.WTTRDFIN5D, 0.90),
            }
        )
    return pd.DataFrame(rows).sort_values("raw_n", ascending=False)


def format_markdown_table(frame: pd.DataFrame, digits: int = 3) -> str:
    display = frame.copy()
    for column in display.select_dtypes(include=["number"]).columns:
        display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{value:.{digits}f}")
    headers = [str(column) for column in display.columns]
    rows = [headers] + display.astype(str).values.tolist()
    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    output = ["| " + " | ".join(value.ljust(widths[i]) for i, value in enumerate(rows[0])) + " |"]
    output.append("| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |")
    for row in rows[1:]:
        output.append("| " + " | ".join(value.ljust(widths[i]) for i, value in enumerate(row)) + " |")
    return "\n".join(output)


def create_figures(data: pd.DataFrame, numeric_corr: pd.DataFrame, group_tables: dict[str, pd.DataFrame]) -> list[str]:
    sns.set_theme(style="whitegrid", font_scale=0.95)
    created = []

    valid_duration = data.TRVLCMIN.dropna()
    p99 = valid_duration.quantile(0.99)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7))
    sns.histplot(valid_duration.loc[valid_duration <= p99], bins=35, ax=axes[0], color="#2563eb")
    axes[0].axvline(valid_duration.median(), color="#b91c1c", linestyle="--", label=f"Median {valid_duration.median():.0f} min")
    axes[0].set_title("Commute duration through the 99th percentile")
    axes[0].set_xlabel("Minutes")
    axes[0].legend()
    sns.histplot(np.log1p(valid_duration), bins=40, ax=axes[1], color="#0f766e")
    axes[1].set_title("Log-transformed duration, all valid trips")
    axes[1].set_xlabel("log(1 + minutes)")
    fig.tight_layout()
    path = OUT / "duration_distribution.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    created.append(path.name)

    scatter = data[["GCDWORK", "TRVLCMIN", "mode_3cat"]].dropna()
    x99 = scatter.GCDWORK.quantile(0.99)
    y99 = scatter.TRVLCMIN.quantile(0.99)
    scatter = scatter.loc[scatter.GCDWORK.le(x99) & scatter.TRVLCMIN.le(y99)]
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    sns.scatterplot(data=scatter, x="GCDWORK", y="TRVLCMIN", hue="mode_3cat", alpha=0.32, s=22, ax=ax)
    sns.regplot(data=scatter.loc[scatter.mode_3cat.eq("car")], x="GCDWORK", y="TRVLCMIN", scatter=False, lowess=True, color="#1d4ed8", ax=ax)
    ax.set_title("Home-work distance and duration (through each 99th percentile)")
    ax.set_xlabel("Great-circle home-work distance (miles)")
    ax.set_ylabel("Reported duration (minutes)")
    fig.tight_layout()
    path = OUT / "distance_duration_by_mode.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    created.append(path.name)

    plot_table = group_tables["mode_3cat"].sort_values("weighted_median_minutes")
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    bars = ax.barh(plot_table.group, plot_table.weighted_median_minutes, color=["#2563eb", "#0f766e", "#b45309"][: len(plot_table)])
    for bar, n in zip(bars, plot_table.raw_n):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2, f"n={int(n):,}", va="center")
    ax.set_title("Survey-weighted median commute duration by mode")
    ax.set_xlabel("Minutes")
    ax.set_ylabel("")
    fig.tight_layout()
    path = OUT / "duration_by_mode.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    created.append(path.name)

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(numeric_corr, dtype=bool), k=1)
    sns.heatmap(numeric_corr, mask=mask, cmap="vlag", vmin=-1, vmax=1, center=0, annot=True, fmt=".2f", ax=ax)
    ax.set_title("Spearman relationships among numerical and ordered fields")
    fig.tight_layout()
    path = OUT / "numeric_association_heatmap.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    created.append(path.name)
    return created


def write_html_report(summary: dict, tables: dict[str, pd.DataFrame], figures: list[str]) -> None:
    style = """
    body { font-family: Arial, sans-serif; color:#172033; max-width:1180px; margin:30px auto; line-height:1.45; }
    h1,h2,h3 { color:#12355b; } h1 { border-bottom:3px solid #2563eb; padding-bottom:8px; }
    table { border-collapse:collapse; width:100%; margin:12px 0 25px; font-size:13px; }
    th { background:#12355b; color:white; text-align:left; } th,td { padding:7px 9px; border-bottom:1px solid #d7deea; }
    tr:nth-child(even) { background:#f6f8fb; } .note { background:#eef6ff; border-left:4px solid #2563eb; padding:12px; }
    .warning { background:#fff7ed; border-left:4px solid #b45309; padding:12px; }
    img { max-width:100%; margin:10px 0 25px; border:1px solid #d7deea; }
    code { background:#eef2f7; padding:2px 4px; }
    """
    table_sections = []
    for title, frame in tables.items():
        table_sections.append(f"<h2>{html.escape(title)}</h2>{frame.to_html(index=False, border=0, float_format=lambda x: f'{x:.3f}')}")
    figure_sections = "".join(f"<img src='{html.escape(name)}' alt='{html.escape(name)}'>" for name in figures)
    content = f"""<!doctype html><html><head><meta charset='utf-8'><title>NHTS Question 4 exploration</title><style>{style}</style></head><body>
    <h1>NHTS 2022 Question 4: commute-duration exploration</h1>
    <div class='note'><strong>Proposed question:</strong> For adult weekday home-based work trips, how accurately can home-work distance, planned mode, departure period, trip direction, and broad residential context predict reported trip duration?</div>
    <p>The analysis contains {summary['valid_duration_n']:,} trips with valid duration from {summary['trip_n']:,} eligible trips, representing {summary['people_n']:,} people in {summary['household_n']:,} households. The unweighted median duration is {summary['median_minutes']:.1f} minutes; the survey-weighted median is {summary['weighted_median_minutes']:.1f} minutes.</p>
    <div class='warning'><strong>Interpretation boundary:</strong> exploratory associations are descriptive. Actual trip miles are shown only as a leakage diagnostic. Final prediction must split by household, perform all preprocessing inside training folds, retain an untouched test set, and avoid causal language.</div>
    {''.join(table_sections)}
    <h2>Figures</h2>{figure_sections}
    <h2>Recommended proposal resolution</h2>
    <ol><li>Use reported duration in minutes as the outcome and adult weekday home-based work trips as the population.</li>
    <li>Define prediction time as immediately before departure, after planned mode is known. This makes mode and departure period eligible while excluding realised trip miles.</li>
    <li>Use a median-duration rule as baseline, a transparent Gamma/log-linear or quantile regression as the main model, and a random forest or gradient-boosted tree as the nonlinear benchmark.</li>
    <li>Use household-grouped cross-validation and reserve a final household or Census-division holdout. Report MAE and median absolute error in minutes, tail error, calibration of prediction intervals, and subgroup performance.</li>
    <li>Pre-register sensitivity analyses for zero/extreme durations, missing <code>GCDWORK</code>, car-only trips, outbound home-to-work trips, survey weights, and alternative density measures.</li></ol>
    </body></html>"""
    (OUT / "NHTS_2022_q4_commute_duration_report.html").write_text(content, encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    if not SOURCE.exists() or not RAW_TRIPS.exists():
        raise FileNotFoundError("Required NHTS source files were not found in the project folder.")

    data = pd.read_csv(SOURCE, low_memory=False)
    raw_trips = pd.read_csv(
        RAW_TRIPS,
        usecols=["TDCASEID", "R_AGE", "TDWKND", "TRIPPURP", "TRPTRANS"],
        low_memory=False,
    )
    accepted_modes = {1, 2, 3, 4, 8, 10, 11, 12, 13, 18, 20}
    expected = raw_trips.loc[
        raw_trips.R_AGE.ge(18)
        & raw_trips.TDWKND.eq(2)
        & raw_trips.TRIPPURP.eq(1)
        & raw_trips.TRPTRANS.isin(accepted_modes)
    ]
    if set(expected.TDCASEID) != set(data.TDCASEID):
        raise AssertionError("The saved analysis file no longer matches the intended raw-trip population.")
    if data.TDCASEID.duplicated().any():
        raise AssertionError("TDCASEID must uniquely identify commute-trip rows.")
    if data[["HOUSEID", "PERSONID", "TDCASEID"]].isna().any().any():
        raise AssertionError("Required household, person, or trip identifiers are missing.")

    data = derive_fields(data)
    data = clean_special_codes(data, NUMERIC_FIELDS + ["STRTTIME"])
    data["TRAVDAY"] = data["travel_day_label"]

    variable_profile = []
    for spec in VARIABLES:
        series = data[spec.name]
        variable_profile.append(
            {
                "variable": spec.name,
                "label": spec.label,
                "role": spec.role,
                "kind": spec.kind,
                "valid_n": int(series.notna().sum()),
                "missing_pct": 100 * series.isna().mean(),
                "distinct": int(series.nunique(dropna=True)),
                "dominant_pct": 100 * series.value_counts(normalize=True, dropna=True).iloc[0] if series.notna().any() else np.nan,
            }
        )
    variable_profile = pd.DataFrame(variable_profile)
    variable_profile.to_csv(OUT / "variable_profile.csv", index=False)

    duration = data.TRVLCMIN.dropna()
    weight_valid = data.loc[data.TRVLCMIN.notna() & data.WTTRDFIN5D.gt(0), ["TRVLCMIN", "WTTRDFIN5D"]]
    effective_n = weight_valid.WTTRDFIN5D.sum() ** 2 / (weight_valid.WTTRDFIN5D.pow(2).sum())
    duration_summary = pd.DataFrame(
        [
            {
                "trip_n": len(data),
                "valid_duration_n": len(duration),
                "missing_duration_n": int(data.TRVLCMIN.isna().sum()),
                "zero_duration_n": int(duration.eq(0).sum()),
                "people_n": data[["HOUSEID", "PERSONID"]].drop_duplicates().shape[0],
                "household_n": data.HOUSEID.nunique(),
                "mean_minutes": duration.mean(),
                "median_minutes": duration.median(),
                "p90_minutes": duration.quantile(0.90),
                "p95_minutes": duration.quantile(0.95),
                "p99_minutes": duration.quantile(0.99),
                "maximum_minutes": duration.max(),
                "skewness": duration.skew(),
                "weighted_median_minutes": weighted_quantile(weight_valid.TRVLCMIN, weight_valid.WTTRDFIN5D, 0.50),
                "weighted_p90_minutes": weighted_quantile(weight_valid.TRVLCMIN, weight_valid.WTTRDFIN5D, 0.90),
                "weight_effective_sample_size": effective_n,
            }
        ]
    )
    duration_summary.to_csv(OUT / "duration_summary.csv", index=False)

    numeric_rows = []
    for field in [name for name in NUMERIC_FIELDS if name != "TRVLCMIN"]:
        pair = data[[field, "TRVLCMIN", "WTTRDFIN5D"]].dropna()
        rho = pair[[field, "TRVLCMIN"]].corr(method="spearman").iloc[0, 1] if len(pair) >= 3 else np.nan
        weighted_rho = weighted_spearman(pair[field], pair.TRVLCMIN, pair.WTTRDFIN5D)
        ci_low, ci_high = cluster_bootstrap_spearman(data, field)
        numeric_rows.append(
            {
                "predictor": field,
                "label": LABELS[field],
                "role": ROLES[field],
                "complete_n": len(pair),
                "missing_pct": 100 * data[field].isna().mean(),
                "spearman_rho": rho,
                "cluster_bootstrap_ci_low": ci_low,
                "cluster_bootstrap_ci_high": ci_high,
                "weighted_spearman_rho": weighted_rho,
            }
        )
    numeric_assoc = pd.DataFrame(numeric_rows).sort_values("spearman_rho", key=lambda x: x.abs(), ascending=False)
    numeric_assoc.to_csv(OUT / "numeric_duration_associations.csv", index=False)

    categorical_rows = []
    for field in CATEGORICAL_FIELDS:
        eta, n = rank_eta(data[field], data.TRVLCMIN)
        categorical_rows.append(
            {
                "predictor": field,
                "label": LABELS[field],
                "role": ROLES[field],
                "complete_n": n,
                "levels": int(data[field].nunique(dropna=True)),
                "rank_eta": eta,
                "dominant_level_pct": 100 * data[field].value_counts(normalize=True, dropna=True).iloc[0],
            }
        )
    categorical_assoc = pd.DataFrame(categorical_rows).sort_values("rank_eta", ascending=False)
    categorical_assoc.to_csv(OUT / "categorical_duration_associations.csv", index=False)

    cramer_rows = []
    for first, second in combinations(CATEGORICAL_FIELDS, 2):
        value, n, rows, columns = bias_corrected_cramers_v(data[first], data[second])
        cramer_rows.append(
            {
                "categorical_1": first,
                "categorical_2": second,
                "cramers_v_corrected": value,
                "complete_n": n,
                "levels_1": rows,
                "levels_2": columns,
            }
        )
    cramer_pairs = pd.DataFrame(cramer_rows).sort_values("cramers_v_corrected", ascending=False)
    cramer_pairs.to_csv(OUT / "categorical_predictor_cramers_v.csv", index=False)

    corr_fields = ["TRVLCMIN", "GCDWORK", "TRPMILES", "R_AGE", "HHFAMINC_IMP", "HHVEHCNT", "HBPPOPDN", "HBRESDN", "HTRESDN"]
    numeric_corr = data[corr_fields].corr(method="spearman", min_periods=100)
    numeric_corr.to_csv(OUT / "numeric_spearman_matrix.csv")
    pair_rows = []
    for first, second in combinations([f for f in corr_fields if f != "TRVLCMIN"], 2):
        pair = data[[first, second]].dropna()
        pair_rows.append(
            {
                "numeric_1": first,
                "numeric_2": second,
                "spearman_rho": pair.corr(method="spearman").iloc[0, 1] if len(pair) >= 3 else np.nan,
                "complete_n": len(pair),
            }
        )
    numeric_pairs = pd.DataFrame(pair_rows).sort_values("spearman_rho", key=lambda x: x.abs(), ascending=False)
    numeric_pairs.to_csv(OUT / "numeric_predictor_pairs.csv", index=False)

    group_fields = ["mode_3cat", "trip_direction", "departure_period", "TRAVDAY", "RAIL", "URBRUR", "MSACAT"]
    group_tables = {}
    for field in group_fields:
        table = summarise_group(data, field)
        group_tables[field] = table
        table.to_csv(OUT / f"duration_by_{field}.csv", index=False)

    missing_rows = []
    for field in ["GCDWORK", "STRTTIME", "TRVLCMIN"]:
        missing = data[field].isna().astype(int)
        for category in ["mode_3cat", "trip_direction", "RAIL", "URBRUR"]:
            value, n, rows, columns = bias_corrected_cramers_v(missing, data[category])
            missing_rows.append(
                {
                    "missing_field": field,
                    "categorical_field": category,
                    "missing_n": int(missing.sum()),
                    "cramers_v_corrected": value,
                    "complete_n": n,
                }
            )
    missingness = pd.DataFrame(missing_rows).sort_values("cramers_v_corrected", ascending=False)
    missingness.to_csv(OUT / "missingness_associations.csv", index=False)

    p99 = duration.quantile(0.99)
    full_pair = data[["GCDWORK", "TRVLCMIN"]].dropna()
    restricted_pair = full_pair.loc[full_pair.TRVLCMIN.le(p99)]
    sensitivity = pd.DataFrame(
        [
            {
                "analysis": "all valid duration values",
                "n": len(full_pair),
                "duration_max": full_pair.TRVLCMIN.max(),
                "duration_median": full_pair.TRVLCMIN.median(),
                "gcdwork_duration_spearman": full_pair.corr(method="spearman").iloc[0, 1],
            },
            {
                "analysis": "duration at or below sample p99",
                "n": len(restricted_pair),
                "duration_max": restricted_pair.TRVLCMIN.max(),
                "duration_median": restricted_pair.TRVLCMIN.median(),
                "gcdwork_duration_spearman": restricted_pair.corr(method="spearman").iloc[0, 1],
            },
        ]
    )
    sensitivity.to_csv(OUT / "extreme_value_sensitivity.csv", index=False)

    mode_specific = []
    for mode, group in data.groupby("mode_3cat", observed=True):
        pair = group[["GCDWORK", "TRVLCMIN"]].dropna()
        mode_specific.append(
            {
                "mode": mode,
                "complete_n": len(pair),
                "gcdwork_duration_spearman": pair.corr(method="spearman").iloc[0, 1] if len(pair) >= 10 else np.nan,
                "median_duration": pair.TRVLCMIN.median() if len(pair) else np.nan,
                "median_gcdwork": pair.GCDWORK.median() if len(pair) else np.nan,
            }
        )
    mode_specific = pd.DataFrame(mode_specific).sort_values("complete_n", ascending=False)
    mode_specific.to_csv(OUT / "distance_duration_by_mode.csv", index=False)

    figures = create_figures(data, numeric_corr, group_tables)

    summary = duration_summary.iloc[0].to_dict()
    strongest_numeric = numeric_assoc.loc[numeric_assoc.role.ne("leakage diagnostic")].iloc[0]
    strongest_categorical = categorical_assoc.iloc[0]
    high_cramer = cramer_pairs.loc[cramer_pairs.cramers_v_corrected.ge(0.50)].head(8)
    high_numeric = numeric_pairs.loc[numeric_pairs.spearman_rho.abs().ge(0.70)].head(8)
    manifest = {
        "source": SOURCE.name,
        "raw_verification_source": str(RAW_TRIPS.relative_to(ROOT)),
        "output_directory": OUT.name,
        "bootstrap_repetitions": BOOTSTRAP_REPS,
        "random_seed": RNG_SEED,
        "trip_n": int(summary["trip_n"]),
        "valid_duration_n": int(summary["valid_duration_n"]),
        "created_files": sorted([path.name for path in OUT.iterdir() if path.is_file()]),
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    proposal = f"""# Proposal evidence for Question 4: commute duration

## Recommended primary question

> For adults making weekday home-based work trips in the United States, how accurately can home-work distance, planned transport mode, departure period, trip direction, and broad residential context predict reported trip duration?

The intended prediction time is **immediately before departure, after the planned mode is known**. This decision makes mode and departure period legitimate candidate predictors. It excludes realised trip miles (`TRPMILES`) because that value describes the journey that occurred.

## Why this question is feasible

- The curated population contains **{int(summary['trip_n']):,} trips**, **{int(summary['people_n']):,} people**, and **{int(summary['household_n']):,} households**.
- Duration is available for **{int(summary['valid_duration_n']):,} trips**. Its median is **{summary['median_minutes']:.1f} minutes**, its 90th percentile is **{summary['p90_minutes']:.1f} minutes**, and its maximum is **{summary['maximum_minutes']:.0f} minutes**.
- The survey-weighted median is **{summary['weighted_median_minutes']:.1f} minutes**. The weight effective sample size is approximately **{summary['weight_effective_sample_size']:.0f}**, showing why raw sample size and weighted population estimates should both be reported.
- The strongest eligible numerical relationship with duration is **{strongest_numeric.predictor}** (Spearman rho **{strongest_numeric.spearman_rho:.3f}**, household-cluster bootstrap 95% interval **[{strongest_numeric.cluster_bootstrap_ci_low:.3f}, {strongest_numeric.cluster_bootstrap_ci_high:.3f}]**).
- The strongest categorical separation is **{strongest_categorical.predictor}** (rank eta **{strongest_categorical.rank_eta:.3f}**). Rank eta is unsigned and descriptive.

## Data curation plan

1. Start from the trip table and retain adults (`R_AGE >= 18`), weekdays (`TDWKND = 2`), home-based work trips (`TRIPPURP = 1`), and car, public-transport, walking, or cycling modes.
2. Preserve `HOUSEID`, `PERSONID`, and `TDCASEID`. One row is one trip; people and households can contribute multiple trips.
3. Derive direction from `WHYFROM` and `WHYTO`, and derive interpretable departure periods from `STRTTIME`.
4. Treat -1, -7, -8, and -9 as documented special codes, not zeros. Keep genuine zero-minute durations visible and investigate them.
5. Use `WTTRDFIN5D` for weekday population summaries. Present raw counts beside weighted estimates.
6. Select one home-density definition before modelling. Do not put all strongly correlated density measures in the same transparent model.
7. Freeze the raw data and record all filters, recodes, exclusions, joins, and missing-data decisions.

## Proposed tools

- **Exploration:** distributions and quantiles; weighted and unweighted group summaries; Spearman correlation; rank eta; bias-corrected Cramer's V; missingness comparisons; and sensitivity to extreme durations.
- **Baseline:** the training-set median duration, optionally stratified only by planned mode if this is pre-registered.
- **Transparent main model:** Gamma regression with a log link, log-duration regression, or median quantile regression. Choose after residual and zero-value diagnostics.
- **Nonlinear benchmark:** random forest or gradient-boosted trees with constrained tuning.
- **Uncertainty:** household-cluster bootstrap confidence intervals for descriptive statistics and resampling variability for test metrics.

## Validation plan

1. Put every trip from the same `HOUSEID` in the same partition. This also keeps each person together.
2. Reserve the final test set before feature selection. Use household-grouped cross-validation inside the remaining development sample.
3. If the stated use is transfer to a new region, use a Census-division holdout; otherwise use a household holdout and report regional subgroup performance.
4. Fit imputation, transformations, feature selection, and tuning only on training folds.
5. Report MAE and median absolute error in minutes, 90th-percentile absolute error, interval coverage where applicable, and errors by mode, direction, urban/rural status, and duration band.
6. Compare survey-weighted and unweighted performance, with raw test counts for every subgroup.

## Pre-registered sensitivity analyses

- All valid durations versus a clearly labelled analysis through the 99th percentile; do not silently delete extremes.
- Complete-case `GCDWORK` analysis versus a missing-indicator or training-fold imputation strategy.
- All included modes versus car-only trips, because public-transport and active-travel samples are small.
- All home-based work trips versus the stricter home-to-work direction.
- One selected density measure versus reasonable alternatives.
- Weighted versus unweighted estimation and evaluation.
- A model excluding mode if the intended prediction time is before mode selection.

## Defence focus

- **Prediction time:** explain exactly when mode and departure time become known.
- **Leakage:** `TRPMILES` is a realised journey measure and is diagnostic only.
- **Repeated observations:** ordinary random row splitting would leak household/person information.
- **Outcome shape:** duration is right-skewed, contains extreme observations, and may contain valid or erroneous zeros.
- **Survey design:** weights change population summaries but do not create more independent observations.
- **Mode imbalance:** separate transit and active-travel error estimates will be uncertain.
- **Measurement:** reported duration and straight-line distance contain measurement error; `GCDWORK` is not route distance.
- **Scope:** the results are predictive/associational, not the causal effect of mode, rail, density, or any policy.

## Redundancy checks to mention

### Strong categorical overlaps (bias-corrected Cramer's V at least 0.50)

{format_markdown_table(high_cramer, 3) if len(high_cramer) else 'No categorical pair reached the stated threshold.'}

### Strong numerical overlaps (absolute Spearman rho at least 0.70)

{format_markdown_table(high_numeric, 3) if len(high_numeric) else 'No numerical pair reached the stated threshold.'}

## Files to use when writing the proposal

- `duration_summary.csv`: sample and outcome facts.
- `variable_profile.csv`: completeness and dominant values.
- `numeric_duration_associations.csv`: numerical relationships and cluster-bootstrap intervals.
- `categorical_duration_associations.csv`: categorical separation in ranked duration.
- `categorical_predictor_cramers_v.csv`: overlap among categorical predictors.
- `numeric_predictor_pairs.csv`: redundant numerical measures.
- `duration_by_*.csv`: group-specific raw and weighted summaries.
- `missingness_associations.csv`: whether missingness is concentrated in observed groups.
- `extreme_value_sensitivity.csv`: effect of the longest durations.
- `distance_duration_by_mode.csv`: whether the core distance-duration relationship differs by mode.

The association tables are screening evidence, not a final predictor-selection algorithm and not inferential proof.
"""
    (OUT / "proposal_evidence.md").write_text(proposal, encoding="utf-8")

    html_tables = {
        "Outcome and sample summary": duration_summary,
        "Numerical relationships with duration": numeric_assoc,
        "Categorical relationships with duration": categorical_assoc,
        "Duration by mode": group_tables["mode_3cat"],
        "Duration by direction": group_tables["trip_direction"],
        "Duration by departure period": group_tables["departure_period"],
        "Strong categorical predictor overlaps": high_cramer,
        "Strong numerical predictor overlaps": high_numeric,
        "Extreme-value sensitivity": sensitivity,
        "Distance-duration relationship by mode": mode_specific,
    }
    write_html_report(summary, html_tables, figures)

    manifest["created_files"] = sorted([path.name for path in OUT.iterdir() if path.is_file()])
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("Question 4 exploration completed.")
    print(f"Trips: {int(summary['trip_n']):,}; valid duration: {int(summary['valid_duration_n']):,}")
    print(f"Median duration: {summary['median_minutes']:.1f} minutes; weighted median: {summary['weighted_median_minutes']:.1f}")
    print(f"Strongest eligible numerical relationship: {strongest_numeric.predictor}, rho={strongest_numeric.spearman_rho:.3f}")
    print(f"Strongest categorical separation: {strongest_categorical.predictor}, rank eta={strongest_categorical.rank_eta:.3f}")
    print(f"Proposal evidence: {OUT / 'proposal_evidence.md'}")
    print(f"HTML report: {OUT / 'NHTS_2022_q4_commute_duration_report.html'}")


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        main()
