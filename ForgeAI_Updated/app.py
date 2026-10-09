import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

st.set_page_config(page_title='ForgeAI | Bottleneck Intelligence', page_icon='🏭', layout='wide')
st.title('🏭 ForgeAI — Production Bottleneck Intelligence')
st.caption('Production-stage risk analysis using the organizer-provided machine event dataset.')
st.info('This version is adapted to the college dataset. It summarizes the provided bottleneck_risk labels and operational metrics. It is a decision-support prototype, not a newly trained forecasting model.')

with st.sidebar:
    st.header('Data source')
    uploaded = st.file_uploader('Upload production CSV', type=['csv'])
    st.caption('Expected dataset fields include stage, bottleneck_risk, processing_time_sec, queue_time_min, material_wait_min, completed_units and sensor readings.')

try:
    if uploaded is not None:
        raw = pd.read_csv(uploaded)
        source_name = uploaded.name
    else:
        default_path = Path(__file__).parent / 'data_iare.csv'
        if default_path.exists():
            raw = pd.read_csv(default_path)
            source_name = 'data_iare.csv (organizer dataset)'
        else:
            st.warning('Upload data_iare.csv to start the analysis.')
            st.stop()
except Exception as e:
    st.error(f'Could not read CSV: {e}')
    st.stop()

df = raw.copy()
df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
st.subheader('1. Dataset preview')
st.caption(f'Data source: {source_name} · {len(df):,} rows · {len(df.columns)} columns')
st.dataframe(df.head(20), use_container_width=True)

st.subheader('2. Data quality')
a,b,c = st.columns(3)
a.metric('Missing cells', int(df.isna().sum().sum()))
b.metric('Duplicate rows', int(df.duplicated().sum()))
c.metric('Numeric columns', int(df.select_dtypes(include='number').shape[1]))
with st.expander('Missing values by column'):
    st.dataframe(df.isna().sum().rename('missing_count').to_frame(), use_container_width=True)

if 'stage' not in df.columns:
    st.error("This dataset needs a 'stage' column for stage-level analysis.")
    st.stop()
df['stage'] = df['stage'].astype('string').str.strip().str.title().fillna('Unknown')
for col in ['bottleneck_risk','failure_risk','defect_type','root_cause_stage']:
    if col in df.columns:
        df[col] = df[col].astype('string').str.strip().str.title()

st.subheader('3. Production overview')
x1,x2,x3,x4 = st.columns(4)
x1.metric('Production events', f'{len(df):,}')
x1; x2.metric('Stages', int(df['stage'].nunique()))
if 'bottleneck_risk' in df.columns:
    risks = df['bottleneck_risk'].dropna().str.lower()
    x3.metric('High bottleneck-risk events', int((risks == 'high').sum()))
    x4.metric('Risk labels available', f'{df["bottleneck_risk"].notna().sum():,}')
else:
    x3.metric('High bottleneck-risk events', 'Not available')
    x4.metric('Risk labels available', 'Not available')

st.subheader('4. Bottleneck analysis by stage')
num_cols = [c for c in ['processing_time_sec','cycle_time_sec','queue_time_min','material_wait_min','completed_units','scheduled_units','temperature_c','vibration_mm_s','pressure_bar','motor_current_a','rpm','quality_score'] if c in df.columns]
agg = {c:'mean' for c in num_cols}
if 'event_id' in df.columns: agg['event_id'] = 'count'
summary = df.groupby('stage', dropna=False).agg(agg).rename(columns={'event_id':'event_count'}).reset_index()
if 'bottleneck_risk' in df.columns:
    risk = pd.crosstab(df['stage'], df['bottleneck_risk'], normalize='index').mul(100).round(1).reset_index()
    risk.columns = [str(c).lower().replace(' ', '_') if c != 'stage' else c for c in risk.columns]
    summary = summary.merge(risk, on='stage', how='left')
    if 'high' in summary.columns:
        summary['high_bottleneck_risk_pct'] = summary['high']
    else: summary['high_bottleneck_risk_pct'] = 0.0
else:
    summary['high_bottleneck_risk_pct'] = float('nan')

if 'high_bottleneck_risk_pct' in summary and summary['high_bottleneck_risk_pct'].notna().any():
    chart = summary.sort_values('high_bottleneck_risk_pct', ascending=False)
    fig, ax = plt.subplots()
    ax.bar(chart['stage'], chart['high_bottleneck_risk_pct'])
    ax.set_title('Share of events labelled High bottleneck risk')
    ax.set_ylabel('High-risk events (%)')
    ax.tick_params(axis='x', rotation=25)
    fig.tight_layout(); st.pyplot(fig); plt.close(fig)
else:
    st.warning('No bottleneck_risk labels found. Showing operational metric summaries only.')

metric_choice = st.selectbox('Choose an operational metric to compare by stage', options=num_cols, index=num_cols.index('queue_time_min') if 'queue_time_min' in num_cols else 0) if num_cols else None
if metric_choice:
    metric_summary = df.groupby('stage')[metric_choice].mean().sort_values(ascending=False)
    fig2, ax2 = plt.subplots()
    ax2.bar(metric_summary.index, metric_summary.values)
    ax2.set_title(f'Average {metric_choice.replace("_", " ")} by stage')
    ax2.set_ylabel(metric_choice.replace('_',' ').title())
    ax2.tick_params(axis='x', rotation=25)
    fig2.tight_layout(); st.pyplot(fig2); plt.close(fig2)

st.dataframe(summary.sort_values('high_bottleneck_risk_pct', ascending=False) if 'high_bottleneck_risk_pct' in summary else summary, use_container_width=True)

st.subheader('5. Recommended investigation')
if 'bottleneck_risk' in df.columns:
    high_rows = df[df['bottleneck_risk'].astype('string').str.strip().str.lower().eq('high')]
    if not high_rows.empty:
        st.write(f'The provided dataset labels {len(high_rows)} events as High bottleneck risk. Use these as investigation priorities, not proof of cause.')
        if 'stage' in high_rows.columns:
            stage_counts = high_rows['stage'].value_counts().head(3)
            for stage, count in stage_counts.items():
                st.markdown(f'**{stage}** — {count} events labelled High')
                st.write('Suggested check: review queue time, material wait, cycle/processing time and maintenance records for this stage before changing the schedule.')
    else:
        st.write('No rows are labelled High after normalizing label capitalization.')
else:
    st.write('Review stages with comparatively high queue time or processing time, then validate with the production team.')

st.subheader('6. Download analysis')
st.download_button('Download stage analysis CSV', data=summary.to_csv(index=False).encode('utf-8'), file_name='forgeai_stage_analysis.csv', mime='text/csv')
st.caption('Data-quality note: missing fields are retained for transparency; summary metrics ignore missing numeric values. Risk labels are supplied in the dataset and are not model predictions generated by this prototype.')
