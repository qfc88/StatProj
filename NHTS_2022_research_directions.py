"""Reproducible exploratory column associations and research-direction discovery.

Run from the project directory. Uses local CSVs and the official local dictionary.
No source files are changed. Outputs are descriptive, not inferential estimates.
"""
from pathlib import Path
from itertools import combinations
import json
import html
import base64
import hashlib

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram, leaves_list
from scipy.spatial.distance import squareform
import openpyxl

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "research_directions"
SPECIAL = {-1, -7, -8, -9}
HOME_DENS = ["HBPPOPDN", "HTPPOPDN", "HBRESDN", "HTRESDN", "HTEEMPDN"]
COUNTS = ["HHSIZE", "NUMADLT", "DRVRCNT", "WRKCOUNT", "HHVEHCNT"]
WORK_DENS = ["WBPPOPDN", "WTPPOPDN", "WTEEMPDN"]
TRIP_DENS = ["DBPPOPDN", "DTPPOPDN", "DTEEMPDN"]
COMMON_CAT = ["RAIL", "URBRUR", "MSACAT", "HOMEOWN", "LIF_CYC"]


def clean_numeric(frame):
    d = frame.copy()
    for c in d:
        if pd.api.types.is_numeric_dtype(d[c]):
            d[c] = d[c].mask(d[c].isin(SPECIAL))
    # Do not reinterpret legitimate questionnaire skips as zeros.
    return d


def cramers_v(x, y):
    pair = pd.concat([x, y], axis=1).dropna()
    tab = pd.crosstab(pair.iloc[:, 0], pair.iloc[:, 1])
    n = len(pair)
    r, k = tab.shape
    if n <= 1 or min(r, k) <= 1:
        return np.nan, n
    chi2 = chi2_contingency(tab, correction=False)[0]
    phi = max(0, chi2 / n - (k - 1) * (r - 1) / (n - 1))
    denom = min(k - 1 - (k - 1)**2 / (n - 1),
                r - 1 - (r - 1)**2 / (n - 1))
    return np.sqrt(phi / denom) if denom > 0 else np.nan, n


def rank_eta(category, numeric):
    """Correlation ratio of numeric ranks by category; unsigned, exploratory."""
    d = pd.DataFrame({"group": category, "value": numeric}).dropna()
    if len(d) < 2 or d.group.nunique() < 2 or d.value.nunique() < 2:
        return np.nan, len(d)
    d["rank"] = d.value.rank()
    mean = d["rank"].mean()
    total = ((d["rank"] - mean)**2).sum()
    between = sum(len(g) * (g["rank"].mean() - mean)**2
                  for _, g in d.groupby("group", observed=True))
    return np.sqrt(between / total), len(d)


def cluster_columns(matrix, kind):
    # Average linkage accepts a dissimilarity; Ward's Euclidean assumption is avoided.
    similarity = matrix.abs() if kind == "spearman" else matrix
    if similarity.isna().any().any():
        raise ValueError("Undefined associations must be resolved before clustering")
    distance = np.clip(1 - similarity.to_numpy(), 0, 1)
    np.fill_diagonal(distance, 0)
    z = linkage(squareform(distance, checks=True), method="average", optimal_ordering=True)
    rows = []
    for threshold in [0.30, 0.45, 0.60]:
        labels = fcluster(z, t=threshold, criterion="distance")
        for c, label in zip(matrix.columns, labels):
            rows.append({"column": c, "distance_cut": threshold, "cluster": int(label)})
    return z, pd.DataFrame(rows)


def analyse_sample(name, raw, num, cat, descriptions):
    d = clean_numeric(raw)
    num = [c for c in num if c in d and d[c].nunique() > 1]
    cat = [c for c in cat if c in d and d[c].nunique() > 1]
    quality = []
    for c in dict.fromkeys(num + cat):
        quality.append({"column": c, "definition": descriptions.get(c, c),
                        "analysis_type": "numeric/ordered" if c in num else "nominal",
                        "valid_n": int(d[c].count()), "missing_pct": 100*d[c].isna().mean(),
                        "distinct": d[c].nunique(),
                        "dominant_pct": 100*d[c].value_counts(normalize=True).iloc[0]})
    quality = pd.DataFrame(quality)
    quality.to_csv(OUT / f"{name}_column_quality.csv", index=False)
    corr = d[num].corr(method="spearman", min_periods=100)
    complete = d[num].notna().astype(int).T.dot(d[num].notna().astype(int))
    pairs = []
    for a, b in combinations(num, 2):
        pairs.append({"column_1": a, "column_2": b, "rho": corr.loc[a, b],
                      "abs_rho": abs(corr.loc[a, b]), "n": int(complete.loc[a, b])})
    pairs = pd.DataFrame(pairs).sort_values("abs_rho", ascending=False)
    corr.to_csv(OUT / f"{name}_spearman.csv")
    complete.to_csv(OUT / f"{name}_pair_counts.csv")
    pairs.to_csv(OUT / f"{name}_correlation_pairs.csv", index=False)
    vmat = pd.DataFrame(np.eye(len(cat)), index=cat, columns=cat)
    vpairs = []
    for a, b in combinations(cat, 2):
        v, n = cramers_v(d[a], d[b])
        vmat.loc[a, b] = vmat.loc[b, a] = v
        vpairs.append({"column_1": a, "column_2": b, "cramers_v": v, "n": n})
    vpairs = pd.DataFrame(vpairs).sort_values("cramers_v", ascending=False)
    vmat.to_csv(OUT / f"{name}_cramers_v.csv")
    vpairs.to_csv(OUT / f"{name}_categorical_pairs.csv", index=False)
    z, members = cluster_columns(corr, "spearman")
    vz, vmembers = cluster_columns(vmat, "nominal")
    members["association"] = "absolute Spearman"
    vmembers["association"] = "bias-corrected Cramer's V"
    members = pd.concat([members, vmembers], ignore_index=True)
    members.to_csv(OUT / f"{name}_column_clusters.csv", index=False)
    order = leaves_list(z)
    sns.set_theme(style="white", font_scale=.85)
    fig = plt.figure(figsize=(15, 13))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 10], width_ratios=[25, 1], hspace=.08, wspace=.12)
    ax = fig.add_subplot(gs[0, 0])
    dendrogram(z, labels=num, ax=ax, no_labels=True, color_threshold=.45)
    ax.axhline(.45, color="#64748b", linestyle="--", linewidth=1)
    ax.set_ylabel("1 - |rho|")
    ax.set_title(f"{name.replace('_', ' ').title()}: groups of numerical and ordered columns\n"
                 f"Average linkage; descriptive, unweighted associations; {len(d):,} rows", loc="left", pad=12)
    ax = fig.add_subplot(gs[1, 0])
    cax = fig.add_subplot(gs[1, 1])
    sns.heatmap(corr.iloc[order, order], cmap="vlag", vmin=-1, vmax=1,
                center=0, ax=ax, cbar_ax=cax, annot=len(num)<=16, fmt=".2f", square=False,
                cbar_kws={"label": "Signed Spearman rho"})
    ax.tick_params(axis="x", rotation=90)
    ax.tick_params(axis="y", rotation=0)
    fig.savefig(OUT / f"{name}_column_clusters.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5))
    dendrogram(vz, labels=cat, ax=ax, color_threshold=.45, leaf_rotation=30)
    ax.axhline(.45, color="#64748b", linestyle="--", linewidth=1)
    ax.set_ylabel("1 - bias-corrected Cramer's V")
    ax.set_title(f"{name.replace('_', ' ').title()}: categorical column clustering", loc="left")
    fig.savefig(OUT / f"{name}_categorical_clusters.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return {"data": d, "numeric": num, "categorical": cat, "quality": quality,
            "corr": corr, "pairs": pairs, "vpairs": vpairs, "clusters": members}


def outcome_associations(sample, outcomes):
    d = sample["data"]
    rows = []
    for target, target_type in outcomes.items():
        for predictor in sample["numeric"] + sample["categorical"]:
            if target == predictor:
                continue
            predtype = "numeric/ordered" if predictor in sample["numeric"] else "nominal"
            pair = d[[target, predictor]].dropna()
            if pair[target].nunique() < 2 or pair[predictor].nunique() < 2:
                continue
            if target_type == "nominal" and predtype == "nominal":
                value, n = cramers_v(d[target], d[predictor])
                measure = "Cramer's V"
            elif target_type != "nominal" and predtype != "nominal":
                value, n = pair.corr(method="spearman").iloc[0, 1], len(pair)
                measure = "Spearman rho"
            else:
                category, numeric = (target, predictor) if target_type == "nominal" else (predictor, target)
                value, n = rank_eta(d[category], d[numeric])
                measure = "Rank eta"
            rows.append({"outcome": target, "predictor": predictor, "measure": measure,
                         "value": value, "absolute_value": abs(value), "n": n})
    return pd.DataFrame(rows).sort_values(["outcome", "measure", "absolute_value"], ascending=[True, True, False])


def research_questions():
    return pd.DataFrame([
        {"Direction":"1. Vehicle access and mode choice", "Question":"Among adults making weekday home-based work trips, how are household vehicle availability and driver status associated with car, public transport, or active travel?",
         "Outcome":"mode_3cat", "Main columns":"HHVEHCNT, DRIVER; adjust for GCDWORK, HHFAMINC_IMP, one home-density measure",
         "Model family":"Categorical outcome / multinomial logistic regression; binary car vs non-car is an alternative",
         "Sample":"4,269 trips; 207 non-car trips", "Evidence":"DRIVER vs mode: V=0.505; HHVEHCNT vs mode: rank eta=0.250",
         "Assessment":"Strong direct continuation of the current project; rare modes limit model complexity."},
        {"Direction":"2. Residential environment and mode", "Question":"How are residential density and metropolitan heavy-rail status associated with transport mode on adult weekday work trips?",
         "Outcome":"mode_3cat", "Main columns":"HTRESDN or HBPPOPDN, RAIL or MSACAT; adjust for GCDWORK, HHVEHCNT, income",
         "Model family":"Categorical outcome / multinomial logistic regression",
         "Sample":"4,269 trips", "Evidence":"HTRESDN vs mode: rank eta=0.254 (n=4,236); RAIL vs mode: V=0.208",
         "Assessment":"Useful planning question. RAIL is metropolitan heavy-rail status, not distance to a station. This overlaps direction 1; choose a main emphasis."},
        {"Direction":"3. Commute duration", "Question":"How are home-work distance, transport mode, and metropolitan context associated with the duration of adult weekday work trips?",
         "Outcome":"TRVLCMIN (minutes)", "Main columns":"GCDWORK, mode_3cat, RAIL or MSACAT; optional age and income",
         "Model family":"Numerical outcome / suitable positive-outcome regression or quantile regression after examining zeros and skew",
         "Sample":"4,266 trips with duration; 3,811 also have GCDWORK", "Evidence":"GCDWORK vs duration: rho=0.726; actual trip miles vs duration: rho=0.826",
         "Assessment":"Clearest numerical-regression alternative. For an explanatory after-trip analysis, mode can be included. Prediction must specify whether mode is already known; actual miles are also observed after travel."},
        {"Direction":"4. Household vehicle ownership", "Question":"How are household income, residential density, and household composition associated with the number of vehicles owned?",
         "Outcome":"HHVEHCNT (vehicle count)", "Main columns":"HHFAMINC_IMP, HBPPOPDN, DRVRCNT or NUMADLT, HOMEOWN",
         "Model family":"Count regression, such as Poisson or negative binomial after dispersion checks; zero-vehicle classification is another outcome",
         "Sample":"7,893 households, including 476 with no vehicles", "Evidence":"Vehicle count vs income: rho=0.391; vs home density: rho=-0.245; vs driver count: rho=0.696",
         "Assessment":"Strong distinct question with one record per household. Vehicle ownership and driver status may be jointly determined; interpretation remains associational."},
        {"Direction":"5. Telework and socioeconomic characteristics", "Question":"Among employed adults, how are education, household income, and residential context associated with frequency of working from home?",
         "Outcome":"WKFMHM22 (four ordered categories)", "Main columns":"EDUC, HHFAMINC_IMP, R_AGE, one home-density measure; optional RAIL or MSACAT",
         "Model family":"Ordinal logistic regression; binary any telework vs never is an alternative classification question",
         "Sample":"7,689 employed adults; all have WKFMHM22", "Evidence":"Telework vs education: rho=0.267; vs income: rho=0.217",
         "Assessment":"Strong separate direction with a larger person sample. The categories are never, 1-2, 3-4, and 5+ days; their codes are not exact numbers of days. Avoid WRKLOC as an ordinary predictor because 'only work at home' overlaps the outcome."},
        {"Direction":"6. Residential environment and commute length", "Question":"Among employed adults with an observed home-work location pair, how are residential density and income associated with home-work distance?",
         "Outcome":"GCDWORK (great-circle miles)", "Main columns":"HBPPOPDN or HBRESDN, HHFAMINC_IMP, R_AGE, EDUC, URBRUR",
         "Model family":"Numerical outcome / distance regression or quantile regression after inspecting skew and zero distances",
         "Sample":"5,665 of 7,689 employed adults have GCDWORK", "Evidence":"Home density vs distance: rho=-0.183 (n=5,633); income vs distance: rho=0.106 (n=5,665)",
         "Assessment":"Feasible but relationships are modest. Missing or inapplicable work locations select the sample; do not use actual trip distance or duration as predictors of home-work distance."},
        {"Direction":"7. Telework and daily travel (tentative)", "Question":"Is usual telework frequency associated with the number of trips made by employed adults on their survey travel day?",
         "Outcome":"CNTTDTR (daily trip count)", "Main columns":"WKFMHM22, EDUC, R_AGE, household composition; add travel-day controls",
         "Model family":"Count regression, with dispersion and excess-zero checks",
         "Sample":"7,689 employed adults, including non-travellers", "Evidence":"Telework vs daily trip count: rho=-0.062",
         "Assessment":"Weak marginal signal; lower priority. Usual telework frequency does not identify whether the respondent worked from home on that specific survey day. Do not describe this as a causal telework effect."}
    ])


def write_report(samples, associations, summary):
    def table(df):
        return df.to_html(index=False, border=0, classes="data", float_format=lambda x:f"{x:.3f}")
    def image_tag(filename, alt):
        encoded = base64.b64encode((OUT/filename).read_bytes()).decode()
        return f'<img src="data:image/png;base64,{encoded}" alt="{html.escape(alt)}">'
    questions = research_questions()
    questions.to_csv(OUT / "research_questions.csv", index=False)
    c = samples["commute"]
    groups = []
    for kind, sub in c["clusters"].query("distance_cut == .45").groupby("association"):
        for label, group in sub.groupby("cluster"):
            groups.append({"Association":kind,"Cluster":label,"Columns":", ".join(group.column),
                           "Status":"Related-column group" if len(group)>1 else "Singleton at this cut"})
    corr_rows = []
    for name, rows in summary["selected_correlations"].items():
        for r in rows:
            corr_rows.append({"Sample":name,"Column 1":r["a"],"Column 2":r["b"],"Spearman rho":r["rho"],"Pair n":r["n"]})
    method = """
    <p>This analysis clusters <strong>columns</strong>, not travellers. It identifies overlapping measurements and helps formulate questions; it does not select a best causal model or prove that a proposed question is novel.</p>
    <ul><li>Numerical and ordered fields: Spearman rank correlation. Density, education, income and telework codes are treated as ordered bands, never exact quantities.</li>
    <li>Nominal pairs: bias-corrected Cramer's V. Numeric codes for urban/rural, sex, tenure and metropolitan status do not imply numerical spacing.</li>
    <li>Nominal versus numerical/ordered outcome: rank eta, the correlation ratio of ranks by category. It is unsigned. V, rank eta and rho are different measures and must not be interpreted as interchangeable effect sizes.</li>
    <li>Average-linkage hierarchical clustering uses 1 - |rho| for numerical/ordered columns and 1 - V for nominal columns. These two types are clustered separately. The displayed cut of 0.45 is a descriptive choice; CSVs also show cuts at 0.30 and 0.60. It is an average-linkage cut, not a guarantee that every within-group pair exceeds 0.55 correlation.</li>
    <li>Pairwise complete observations are used, with at least 100 for Spearman calculations. Pair counts and column missingness are exported. No values are imputed by this analysis. HHFAMINC_IMP uses the survey's already-imputed income field.</li>
    <li>Local codebook special values -1, -7, -8 and -9 are excluded from these calculations; valid skips remain 'not observed/inapplicable' and are not recoded to zero. Conditional-use fields such as PTUSED and TRNPASS are not included in general-purpose clustering.</li>
    <li>Correlations and clustering are unweighted descriptive results. They are not national population estimates. No significance claims or p-value screening are used. Final models need appropriate survey weights/design and dependence handling; prediction splits should keep members of the same household together.</li></ul>
    """
    recommendations = """
    <p><strong>For your current project:</strong> choose direction 1 or 2 as the main question, with a small model. Direction 3 is the clearest switch to a numerical outcome. Directions 4 and 5 are particularly useful alternatives with different units of analysis and broader samples. Directions 6 and 7 are feasible exploratory questions, with weaker observed marginal relationships.</p>
    <p>These are data-supported question candidates, not questions validated by an independent confirmatory study. Subject knowledge and a literature review should guide the final choice; later evaluation should account for this exploratory selection.</p>
    """
    limitations = f"""
    <ul><li>The commute sample contains 4,062 car, 77 public-transport and 130 active-travel trips. These represent 2,265, 52 and 75 distinct people respectively; some people appear in more than one mode. Treating all trips as independent would overstate information.</li>
    <li>Separate walking and cycling have only 99 and 31 trips. Combining them helps sample size but changes the question. Three classes remain strongly imbalanced.</li>
    <li>Home-based work trips include journeys toward home as well as toward work. DB*/DT* fields describe the actual trip destination; they must not automatically be labelled workplace density. WBPPOPDN/WTPPOPDN/WTEEMPDN describe the person's workplace. Their clustering together here partly reflects trip structure.</li>
    <li>RAIL and MSACAT overlap strongly by definition: MSACAT explicitly includes rail status for large metropolitan areas. Their V=0.979 in commute trips is partly constructed redundancy, not a discovery about behaviour. RAIL is not a measure of how close someone lives to a station.</li>
    <li>TRVLCMIN and TRPMILES are realised trip outcomes. Do not use them as ordinary pre-choice predictors of transport mode. If GCDWORK is the outcome, omit trip time/miles to avoid an essentially circular question. If vehicle count is the outcome, omit vehicle-count-derived features.</li>
    <li>Do not automatically include every field in a cluster. Choose representative measures based on the question; related fields can still have distinct meanings. Age, income, education, work hours and telework remain singletons at the displayed commute cut and can still matter.</li>
    <li>For the stable household/person fields, repeating the commute correlations with one row per person changes rho by at most {summary['person_sensitivity_max_abs_rho_change']:.3f}. This limited sensitivity check is not a clustered standard error or cluster-stability proof. Trip-specific destination, distance and duration fields are excluded from it.</li>
    <li>Duration is available for 4,266 trips, with median 21 minutes and maximum 950 minutes. Inspect extreme values and zeros before choosing a regression distribution; do not silently remove them. GCDWORK is missing or inapplicable for 2,024 of the 7,689 workers.</li>
    <li>The three samples answer different population questions. Use trip weights for trip estimates, person weights for person estimates and household weights for household estimates, with the matching weekday/seven-day scope. Household and person analyses should not be restricted to commuters without a reason.</li></ul>
    """
    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
             "<title>NHTS: column clusters and research questions</title><style>body{font:16px/1.6 system-ui,sans-serif;color:#203047;background:#f3f6fa;margin:0}main{max-width:1220px;margin:auto;padding:42px;background:white}h1{font-size:32px;line-height:1.2}h2{margin-top:42px;color:#12365c}h3{margin-top:28px}p{max-width:1050px}.note{border-left:5px solid #2f789b;padding:14px 20px;background:#edf6fa}img{width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}th{text-align:left;background:#e7eef6}th,td{padding:10px;border-bottom:1px solid #d7dfeb;vertical-align:top}tr:nth-child(even){background:#f8fafc}.scroll{overflow-x:auto}code{background:#edf1f6;padding:2px 4px}li{margin:8px 0}summary{cursor:pointer;font-weight:600}footer{font-size:13px;color:#526070;margin-top:40px}@media print{main{padding:0}details{display:block}h2{break-after:avoid}tr,img{break-inside:avoid}}</style><main>",
             "<h1>Which research questions can these columns support?</h1><p>NHTS 2022 local data · Exploratory analysis · 17 October 2026</p>",
             "<div class='note'><strong>Result:</strong> four clear numerical column groups and one categorical overlap emerge in the current commute sample. They support distinct directions on mode choice, commute duration, vehicle ownership and telework. Income and education provide additional explanatory themes but do not form their own tight cluster at the chosen cut.</div>",
             "<h2>1. Samples used</h2>", table(pd.DataFrame([
                 {"Sample":"Current adult weekday home-based work trips","Rows":4269,"Unit":"One trip; 2,384 people in 1,928 households"},
                 {"Sample":"All employed adults (age 18+, WORKER=1)","Rows":7689,"Unit":"One person, including people with no commute trip"},
                 {"Sample":"All households","Rows":7893,"Unit":"One household"}])),
             "<p>The exported commute trip identifiers and mode groups were checked against the raw trip file. Household and person keys were checked for uniqueness. No original data or previous notebooks were modified.</p>",
             "<h2>2. Column clusters in the current commute sample</h2>",
             "<p>The home-density columns form one group. Workplace and trip-destination density columns form another. Household size, adult count, driver count and vehicle count group together. Home-work distance, actual trip distance and duration form a fourth group. Rail status and metropolitan category form a categorical pair. Other columns remain separate at this cut.</p>",
             image_tag("commute_column_clusters.png","Clustered Spearman heatmap and dendrogram for commute columns"),
             image_tag("commute_categorical_clusters.png","Categorical column clustering"),
             "<details><summary>Exact cluster membership, including singletons</summary>", table(pd.DataFrame(groups)), "</details>",
             "<h2>3. Correlations worth knowing before choosing a question</h2>", table(pd.DataFrame(corr_rows)),
             "<p>A positive rho means higher values tend to occur together; a negative rho means one tends to decrease as the other increases. Density and income are ordered categories, so these are relationships between ranks.</p>",
             "<h2>4. Research-question candidates</h2>",recommendations]
    for _,q in questions.iterrows():
        parts += [f"<h3>{html.escape(q.Direction)}</h3><p><strong>{html.escape(q.Question)}</strong></p>",
                  table(pd.DataFrame({"Item":["Outcome","Main columns","Method","Sample","Observed evidence","Assessment"],
                                      "Details":[q.Outcome,q['Main columns'],q['Model family'],q.Sample,q.Evidence,q.Assessment]}))]
    parts += ["<h2>5. Outcome-association results</h2>",
              "<p>These tables include other possible outcomes as descriptive comparators; they are not ready-made predictor sets. Apply the outcome-specific restrictions above. The candidate mode outcome is held outside column clustering.</p>"]
    for name in samples:
        parts += [f"<details><summary>{name.title()}: all candidate outcome associations</summary>",
                  table(associations[name].drop(columns="absolute_value")),"</details>"]
    parts += ["<h2>6. Method and interpretation</h2>",method,"<h2>7. Limits that affect the research choice</h2>",limitations,
              "<h2>8. Other samples and variable definitions</h2>"]
    for name in ["household","workers"]:
        parts += [f"<details><summary>{name.title()}: clustered numerical columns</summary>",
                  image_tag(f"{name}_column_clusters.png",f"{name} clustered heatmap"),"</details>"]
    for name in samples:
        parts += [f"<details><summary>{name.title()}: column definitions and quality</summary>",table(samples[name]["quality"]),"</details>"]
    parts += ["<footer>Sources: local nhts_weekday_commute_analysis.csv; Data/tripv2pub.csv; Data/perv2pub.csv; Data/hhv2pub.csv; official local NHTS_2022_Data_Dictionary_V2.1.xlsx and NHTS_2022_Codebook_V2.1.xlsx. input_manifest.csv records input hashes. All numerical results can be reproduced with NHTS_2022_research_directions.py; detailed matrices, pair counts, memberships at three cuts and question candidates are saved beside this report. The notebook presents the same workflow in Jupyter.</footer></main></html>"]
    (OUT/"NHTS_2022_research_directions.html").write_text("\n".join(parts),encoding="utf-8")
    return questions


def write_notebook():
    import nbformat as nbf
    nb = nbf.v4.new_notebook()
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    nb.cells = [
        md("# NHTS 2022: Column Clustering and Research Directions\n\nThis notebook complements the existing correlation notebook. It groups **columns**, then compares candidate research questions across commute trips, all employed adults, and households. Existing source files are preserved.\n\nUse the installed **Python 3 (ipykernel)** Anaconda environment. Outputs go to `research_directions/`. These are unweighted exploratory associations, not causal effects or national population estimates."),
        code("from pathlib import Path\nimport io\nfrom contextlib import redirect_stdout\nimport pandas as pd\nfrom IPython.display import display, Image\nfrom NHTS_2022_research_directions import run_analysis, research_questions, OUT\n\nwith redirect_stdout(io.StringIO()):\n    samples, associations, summary = run_analysis()\ndisplay(pd.Series(summary['counts'], name='Count').to_frame())"),
        md("## Methods\n\nSpearman rho is used for numerical and ordered variables, including density bands, income, education and telework categories. Bias-corrected Cramer's V is used for nominal pairs. Rank eta measures unsigned separation of numerical ranks among categories. These measures are not interchangeable.\n\nColumns are clustered separately by type with average linkage and dissimilarity `1 - abs(rho)` or `1 - V`. The displayed distance cut is 0.45; membership at 0.30 and 0.60 is also exported. This is exploratory grouping, not an automatically chosen optimal number of clusters.\n\nSpecial codes -1, -7, -8 and -9 are excluded, with no automatic zero recoding for skips. Pairwise complete observations are used. At least 100 complete pairs are required for Spearman. Survey-imputed income is retained as `HHFAMINC_IMP`; this analysis does not impute other values."),
        code("display(Image(filename=str(OUT / 'commute_column_clusters.png')))\ndisplay(Image(filename=str(OUT / 'commute_categorical_clusters.png')))"),
        code("members = samples['commute']['clusters'].query('distance_cut == 0.45')\ndisplay(members.groupby(['association', 'cluster'])['column'].agg(', '.join).to_frame('Columns'))"),
        md("## What the groups mean\n\nThe current sample groups residential-density measurements together, workplace/destination-density measurements together, household size/adults/drivers/vehicles together, and commute distance/time together. Rail status and MSA category overlap by construction. Income, education, age, work hours and telework remain singletons at this cut; they can still be useful.\n\n**Destination is not always workplace:** home-based work trips include trips toward home. The DB*/DT* fields identify a trip's destination, while W* fields identify the person's workplace."),
        code("for name, rows in summary['selected_correlations'].items():\n    print(name.upper())\n    display(pd.DataFrame(rows).rename(columns={'a':'Column 1','b':'Column 2','rho':'Spearman rho','n':'Pair n'}))"),
        md("## Several research questions\n\nDirections 1 and 2 extend the current mode-choice project. Direction 3 is the clearest numerical-regression alternative. Directions 4 and 5 use broader, correctly defined household/person samples. Directions 6 and 7 have more modest marginal evidence. The correlations help assess feasibility; subject knowledge and a literature review remain necessary."),
        code("questions = research_questions()\nfor _, q in questions.iterrows():\n    display(pd.DataFrame({'Item':q.index, 'Details':q.values}))"),
        md("## Candidate outcome associations\n\nTables below are descriptive comparisons, not final predictor lists. If mode is the outcome, omit realised duration and realised trip miles as ordinary pre-choice predictors. If distance is the outcome, do not explain it with another measurement of the same realised journey. Work-location category overlaps telework by definition and should not serve as an ordinary predictor of telework frequency."),
        code("for name, result in associations.items():\n    print(name.upper())\n    display(result.drop(columns='absolute_value'))"),
        md("## Other samples and quality\n\nThe full household sample avoids counting the same household once per commute trip. The employed-adult sample includes workers with no observed commute. Great-circle distance is observed for 5,665 of 7,689 employed adults; inapplicable work locations change the population represented by a distance analysis."),
        code("for name in ['household','workers']:\n    display(Image(filename=str(OUT / f'{name}_column_clusters.png')))\nfor name in samples:\n    print(name.upper())\n    display(samples[name]['quality'])"),
        md("## Limits and next steps\n\n- Commute mode counts are 4,062 car, 77 public transport and 130 active travel. Repeated trips are not independent; final modelling needs household/person dependence and appropriate survey design. Avoid large models for rare categories.\n- Keep household members together in predictive train/test splits.\n- Use trip, person or household weights consistent with the question and travel-day scope. None of the exploratory correlations above is weighted.\n- Telework is four ordered categories, not an exact day count. Do not interpret its code with ordinary linear regression as days.\n- Typical telework frequency does not identify telework on the survey day. The observed rho with daily trips is only -0.062.\n- Choose representative density and composition columns; do not automatically keep every correlated field or mechanically discard all but one.\n- Review zeros, missing locations and outliers before fitting duration/distance models. The largest observed duration is 950 minutes.\n- Equal-person sensitivity for stable attributes is exported; it is not an inferential correction. Cut sensitivity is descriptive and not proof of stable latent constructs.\n\nThe standalone HTML report contains readable research-question assessments, definitions, and these figures. Detailed CSV outputs retain all pair counts and column memberships."),
        code("display(pd.Series(summary['mode_counts'], name='Trips').to_frame())\ndisplay(pd.Series(summary['telework_counts'], name='Workers by telework category').to_frame())\nsensitivity = pd.read_csv(OUT / 'commute_equal_person_sensitivity.csv')\nprint('Largest |rho change| with one row per commuter for stable attributes:',\n      round((sensitivity.trip_rho - sensitivity.one_person_rho).abs().max(), 3))\nprint('HTML report:', OUT / 'NHTS_2022_research_directions.html')")
    ]
    nb.metadata = {"kernelspec":{"display_name":"Python 3 (ipykernel)","language":"python","name":"python3"},
                   "language_info":{"name":"python","version":"3.12.7"}}
    nbf.write(nb, ROOT / "NHTS_2022_research_directions.ipynb")


def run_analysis():
    OUT.mkdir(exist_ok=True)
    dictionary = openpyxl.load_workbook(ROOT / "Data/NHTS_2022_Data_Dictionary_V2.1.xlsx",
                                      read_only=True, data_only=True)
    descriptions = {r[0]: r[3] for r in list(dictionary["Dictionary"].values)[1:]}
    raw = pd.read_csv(ROOT / "nhts_weekday_commute_analysis.csv")
    household = pd.read_csv(ROOT / "Data/hhv2pub.csv")
    person = pd.read_csv(ROOT / "Data/perv2pub.csv")
    source_trips = pd.read_csv(ROOT / "Data/tripv2pub.csv")
    mode_mapping = {1:"car",2:"car",3:"car",4:"car",8:"public_transport",
                    10:"public_transport",11:"public_transport",12:"public_transport",
                    13:"public_transport",18:"active_travel",20:"active_travel"}
    expected = source_trips.loc[(source_trips.R_AGE >= 18) & source_trips.TDWKND.eq(2)
                               & source_trips.TRIPPURP.eq(1) & source_trips.TRPTRANS.isin(mode_mapping)]
    assert set(expected.TDCASEID) == set(raw.TDCASEID), "Export does not match raw commute population"
    assert raw.TRPTRANS.map(mode_mapping).eq(raw.mode_3cat).all()
    workers = person.loc[(person.R_AGE >= 18) & (person.WORKER == 1)].copy()
    assert not household.duplicated("HOUSEID").any()
    assert not person.duplicated(["HOUSEID", "PERSONID"]).any()
    assert not raw.duplicated("TDCASEID").any()
    assert (raw.R_AGE >= 18).all() and raw.TDWKND.eq(2).all() and raw.TRIPPURP.eq(1).all()
    assert raw.mode_3cat.isin(["car", "active_travel", "public_transport"]).all()
    samples = {}
    samples["commute"] = analyse_sample("commute", raw,
        COUNTS + HOME_DENS + WORK_DENS + TRIP_DENS +
        ["R_AGE", "HHFAMINC_IMP", "EDUC", "GCDWORK", "TRPMILES", "TRVLCMIN", "EMPLOYMENT2", "WKFMHM22"],
        COMMON_CAT + ["HOMETYPE", "DRIVER", "R_SEX_IMP", "WRKLOC"], descriptions)
    samples["household"] = analyse_sample("household", household,
        COUNTS + HOME_DENS + ["HHFAMINC_IMP"],
        COMMON_CAT + ["HOMETYPE"], descriptions)
    samples["workers"] = analyse_sample("workers", workers,
        COUNTS + HOME_DENS + WORK_DENS +
        ["R_AGE", "HHFAMINC_IMP", "EDUC", "GCDWORK", "EMPLOYMENT2", "WKFMHM22", "CNTTDTR"],
        COMMON_CAT + ["DRIVER", "R_SEX_IMP", "WRKLOC"], descriptions)
    targets = {"commute": {"mode_3cat": "nominal", "TRVLCMIN": "numeric", "GCDWORK": "numeric"},
               "household": {"HHVEHCNT": "numeric"},
               "workers": {"WKFMHM22": "ordered", "CNTTDTR": "numeric"}}
    associations = {}
    for name, sample in samples.items():
        associations[name] = outcome_associations(sample, targets[name])
        associations[name].to_csv(OUT / f"{name}_outcome_associations.csv", index=False)
    # Equal-person sensitivity: home-work distance/demographic fields otherwise repeat per trip.
    commuter_people = samples["commute"]["data"].sort_values("TDCASEID").drop_duplicates(["HOUSEID", "PERSONID"])
    c = samples["commute"]
    sensitivity = []
    for a, b in combinations(c["numeric"], 2):
        if a in {"TRPMILES", "TRVLCMIN", *TRIP_DENS} or b in {"TRPMILES", "TRVLCMIN", *TRIP_DENS}:
            continue  # Trip outcomes must not be arbitrarily represented by one chosen trip.
        p = commuter_people[[a,b]].dropna()
        sensitivity.append({"column_1":a,"column_2":b,"trip_rho":c["corr"].loc[a,b],
                            "one_person_rho":p.corr(method="spearman").iloc[0,1],"person_n":len(p)})
    pd.DataFrame(sensitivity).to_csv(OUT / "commute_equal_person_sensitivity.csv", index=False)
    manifest = []
    for path in ["nhts_weekday_commute_analysis.csv", "Data/tripv2pub.csv", "Data/perv2pub.csv",
                 "Data/hhv2pub.csv", "Data/NHTS_2022_Data_Dictionary_V2.1.xlsx",
                 "Data/NHTS_2022_Codebook_V2.1.xlsx"]:
        manifest.append({"path":path,"sha256":hashlib.sha256((ROOT/path).read_bytes()).hexdigest()})
    pd.DataFrame(manifest).to_csv(OUT / "input_manifest.csv", index=False)
    samples["commute"]["data"].groupby("mode_3cat")[["TRVLCMIN","TRPMILES","GCDWORK","HHVEHCNT","HTRESDN"]].median().to_csv(OUT / "commute_medians_by_mode.csv")
    sensitivity = pd.DataFrame(sensitivity)
    mode_counts = raw.mode_3cat.value_counts().to_dict()
    mode_people = raw.groupby("mode_3cat")[["HOUSEID","PERSONID"]].apply(lambda x:len(x.drop_duplicates())).to_dict()
    mode_weighted = (raw.groupby("mode_3cat").WTTRDFIN5D.sum()/raw.WTTRDFIN5D.sum()*100).to_dict()
    summary = {"counts": {"commute_trips":len(raw), "commuter_people":len(commuter_people),
                           "commuter_households":raw.HOUSEID.nunique(),"adult_workers":len(workers),
                           "households":len(household)},
               "mode_counts":mode_counts,"mode_people":mode_people,"mode_weighted_pct":mode_weighted,
               "telework_counts":workers.WKFMHM22.value_counts().sort_index().to_dict(),
               "zero_vehicle_households":int(household.HHVEHCNT.eq(0).sum()),
               "person_sensitivity_max_abs_rho_change":float((sensitivity.trip_rho-sensitivity.one_person_rho).abs().max()),
               "clusters":{},"selected_correlations":{}}
    for name, sample in samples.items():
        m = sample["clusters"].query("distance_cut == 0.45")
        summary["clusters"][name] = {kind:{str(k):g.column.tolist() for k,g in sub.groupby("cluster")}
                                     for kind,sub in m.groupby("association")}
    pairs_to_report = {
        "commute":[("TRPMILES","TRVLCMIN"),("GCDWORK","TRVLCMIN"),("GCDWORK","TRPMILES"),
                   ("HBPPOPDN","HBRESDN"),("HBPPOPDN","HTPPOPDN"),("HHVEHCNT","DRVRCNT"),
                   ("HHSIZE","NUMADLT"),("HHFAMINC_IMP","EDUC"),("HBPPOPDN","HHVEHCNT")],
        "household":[("HHVEHCNT","HHFAMINC_IMP"),("HHVEHCNT","DRVRCNT"),("HHVEHCNT","HBPPOPDN")],
        "workers":[("WKFMHM22","EDUC"),("WKFMHM22","HHFAMINC_IMP"),("WKFMHM22","CNTTDTR"),
                   ("GCDWORK","HBPPOPDN"),("GCDWORK","HHFAMINC_IMP")]}
    for name, pairs in pairs_to_report.items():
        summary["selected_correlations"][name] = [
            {"a":a,"b":b,"rho":samples[name]["corr"].loc[a,b],
             "n":int(samples[name]["data"][[a,b]].dropna().shape[0])} for a,b in pairs]
    (OUT / "summary.json").write_text(json.dumps(summary,indent=2,default=lambda v:int(v) if isinstance(v,np.integer) else float(v)), encoding="utf-8")
    write_report(samples, associations, summary)
    print(json.dumps(summary,indent=2))
    for name, a in associations.items():
        print("\n",name,"outcome associations\n", a.groupby(["outcome","measure"],group_keys=False).head(5).to_string(index=False))
    return samples, associations, summary


if __name__ == "__main__":
    run_analysis()
    write_notebook()
