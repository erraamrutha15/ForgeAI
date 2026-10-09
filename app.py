import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

st.set_page_config(page_title="ForgeAI | Bottleneck Intelligence", page_icon="🏭", layout="wide")

st.title("🏭 ForgeAI — Production Bottleneck Intelligence")
st.caption("A decision-support prototype for detecting slow production stages and suggesting practical actions.")

st.info(
    "Demo mode: the default data is fictional sample data for testing the prototype. "
    "Replace it with the organizer-provided dataset after checking its columns. "
    "This first version uses transparent rules, not a trained machine-learning model."
)

SAMPLE_PATH = Path(__file__).parent / "sample_production.csv"

@st.cache_data
def load_sample():
    return pd.read_csv(SAMPLE_PATH)

with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader("Upload production CSV", type=["csv"])
    use_sample = st.checkbox("Use fictional sample data", value=True if uploaded is None else False)
    st.divider()
    st.caption("Expected columns for automatic analysis:")
    st.code("machine, processing_time_min, utilization_pct, downtime_min, units_completed")

try:
    if uploaded is not None:
        raw = pd.read_csv(uploaded)
        source_name = uploaded.name
    elif use_sample:
        raw = load_sample()
        source_name = "sample_production.csv (fictional)"
    else:
        st.warning("Upload a CSV or enable the fictional sample data.")
        st.stop()
except Exception as e:
    st.error(f"Could not read the CSV: {e}")
    st.stop()

st.subheader("1. Dataset preview")
st.caption(f"Data source: {source_name} · {len(raw):,} rows · {len(raw.columns)} columns")
st.dataframe(raw.head(20), use_container_width=True)

# Normalize column names for easier matching.
df = raw.copy()
df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

machine_col = next((c for c in ["machine", "machine_id", "machine_name", "stage", "process", "workstation"] if c in df.columns), None)
time_col = next((c for c in ["processing_time_min", "processing_time", "cycle_time_min", "cycle_time", "processing_minutes"] if c in df.columns), None)
util_col = next((c for c in ["utilization_pct", "utilization", "machine_utilization_pct", "utilization_percent"] if c in df.columns), None)
down_col = next((c for c in ["downtime_min", "downtime", "downtime_minutes"] if c in df.columns), None)
units_col = next((c for c in ["units_completed", "output_units", "units_produced", "production_count"] if c in df.columns), None)

st.subheader("2. Data quality")
quality_a, quality_b, quality_c = st.columns(3)
quality_a.metric("Missing cells", int(df.isna().sum().sum()))
quality_b.metric("Duplicate rows", int(df.duplicated().sum()))
quality_c.metric("Numeric columns", int(df.select_dtypes(include="number").shape[1]))
with st.expander("Missing values by column"):
    st.dataframe(df.isna().sum().rename("missing_count").to_frame(), use_container_width=True)

if machine_col is None:
    st.warning("I couldn't identify a machine/stage column automatically. Rename the relevant column to 'machine' or adjust app.py after inspecting your dataset.")
    st.stop()

# Use available numeric metrics to construct a transparent score.
work = df.copy()
work[machine_col] = work[machine_col].fillna("Unknown").astype(str)
for col in [time_col, util_col, down_col, units_col]:
    if col:
        work[col] = pd.to_numeric(work[col], errors="coerce")

grouped_parts = []
if time_col:
    grouped_parts.append(work.groupby(machine_col)[time_col].mean().rename("avg_processing_time_min"))
if util_col:
    grouped_parts.append(work.groupby(machine_col)[util_col].mean().rename("avg_utilization_pct"))
if down_col:
    grouped_parts.append(work.groupby(machine_col)[down_col].mean().rename("avg_downtime_min"))
if units_col:
    grouped_parts.append(work.groupby(machine_col)[units_col].sum().rename("total_units_completed"))

if not grouped_parts:
    st.error("A machine/stage column was found, but no recognized numeric production metric was found. Check the column names listed in the sidebar and inspect the dataset.")
    st.stop()

summary = pd.concat(grouped_parts, axis=1).reset_index().rename(columns={machine_col: "machine"})
summary["bottleneck_score"] = 0.0
score_notes = []

# Percentile-based, explainable scoring: slower time / higher downtime / very high utilization add risk.
if "avg_processing_time_min" in summary:
    vals = summary["avg_processing_time_min"]
    if vals.notna().sum() > 1 and vals.max() != vals.min():
        summary["bottleneck_score"] += vals.rank(pct=True) * 40
        score_notes.append("higher average processing time")
    else:
        score_notes.append("processing time available but not variable enough to rank")
if "avg_downtime_min" in summary:
    vals = summary["avg_downtime_min"]
    if vals.notna().sum() > 1 and vals.max() != vals.min():
        summary["bottleneck_score"] += vals.rank(pct=True) * 30
        score_notes.append("higher average downtime")
if "avg_utilization_pct" in summary:
    vals = summary["avg_utilization_pct"]
    if vals.notna().sum() > 1 and vals.max() != vals.min():
        summary["bottleneck_score"] += vals.rank(pct=True) * 30
        score_notes.append("higher average utilization")

summary["bottleneck_score"] = summary["bottleneck_score"].round(1)
max_score = summary["bottleneck_score"].max()
if pd.isna(max_score) or max_score == 0:
    summary["risk_level"] = "Insufficient metrics"
else:
    summary["risk_level"] = summary["bottleneck_score"].apply(
        lambda x: "High" if x >= summary["bottleneck_score"].quantile(0.75) else ("Medium" if x >= summary["bottleneck_score"].median() else "Low")
    )

st.subheader("3. Production overview")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Machines / stages", int(summary["machine"].nunique()))
m2.metric("High-risk stages", int((summary["risk_level"] == "High").sum()))
if "avg_utilization_pct" in summary:
    m3.metric("Mean utilization", f"{summary['avg_utilization_pct'].mean():.1f}%")
else:
    m3.metric("Mean utilization", "Not available")
if "avg_downtime_min" in summary:
    m4.metric("Mean downtime", f"{summary['avg_downtime_min'].mean():.1f} min")
else:
    m4.metric("Mean downtime", "Not available")

st.subheader("4. Bottleneck analysis")
st.caption("The score is a transparent heuristic for prioritization, not a calibrated probability of failure or delay.")
left, right = st.columns(2)
with left:
    fig, ax = plt.subplots()
    plot_df = summary.sort_values("bottleneck_score", ascending=False)
    ax.bar(plot_df["machine"], plot_df["bottleneck_score"])
    ax.set_title("Bottleneck priority score by stage")
    ax.set_ylabel("Priority score (relative)")
    ax.set_xlabel("Machine / stage")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
with right:
    metric_to_plot = "avg_processing_time_min" if "avg_processing_time_min" in summary else (
        "avg_downtime_min" if "avg_downtime_min" in summary else "bottleneck_score"
    )
    fig2, ax2 = plt.subplots()
    ax2.bar(summary["machine"], summary[metric_to_plot])
    ax2.set_title(metric_to_plot.replace("_", " ").title() + " by stage")
    ax2.set_xlabel("Machine / stage")
    ax2.tick_params(axis="x", rotation=30)
    fig2.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)

st.dataframe(summary.sort_values("bottleneck_score", ascending=False), use_container_width=True)

st.subheader("5. Recommended actions")
ranked = summary.sort_values("bottleneck_score", ascending=False)
for _, row in ranked.head(3).iterrows():
    machine = row["machine"]
    reasons = []
    if "avg_processing_time_min" in row.index and pd.notna(row.get("avg_processing_time_min")):
        if row["avg_processing_time_min"] >= summary["avg_processing_time_min"].median():
            reasons.append("processing time is at/above the stage median")
    if "avg_downtime_min" in row.index and pd.notna(row.get("avg_downtime_min")):
        if row["avg_downtime_min"] >= summary["avg_downtime_min"].median():
            reasons.append("downtime is at/above the stage median")
    if "avg_utilization_pct" in row.index and pd.notna(row.get("avg_utilization_pct")):
        if row["avg_utilization_pct"] >= summary["avg_utilization_pct"].median():
            reasons.append("utilization is at/above the stage median")
    reason_text = "; ".join(reasons) if reasons else "ranked highly by the available production indicators"
    st.markdown(f"**{machine} — {row['risk_level']} priority**")
    st.write(f"Reason: {reason_text}.")
    st.write("Suggested next step: inspect the stage's job queue and downtime causes; consider shifting suitable work to a stage with spare capacity only after validating skill, machine, and process constraints.")

st.subheader("6. Download analysis")
csv_bytes = summary.to_csv(index=False).encode("utf-8")
st.download_button("Download bottleneck summary CSV", data=csv_bytes, file_name="bottleneck_summary.csv", mime="text/csv")

st.caption("Prototype limitation: no real-time sensors, causal root-cause proof, optimized schedule, or trained forecasting model is included yet. Validate all recommendations with production experts and the real dataset.")
