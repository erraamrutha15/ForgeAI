# ForgeAI — Production Bottleneck Intelligence Prototype

## What this prototype does
- Loads the included fictional sample CSV or an uploaded CSV.
- Shows a data preview and basic data-quality checks.
- Groups production indicators by machine/stage.
- Computes a transparent relative bottleneck-priority score from available processing time, downtime, and utilization.
- Displays charts, suggested investigation steps, and a downloadable summary.

## Important
The included data is fictional. It is only for testing the software. Do not present it as college-provided or real factory data.
The score is a heuristic, not a probability and not proof of causation. The app does not yet perform ML forecasting or mathematically optimize schedules.

## Setup (Windows PowerShell or CMD)
1. Install Python 3.11 or newer if not already installed.
2. Open a terminal in this folder.
3. Create a virtual environment:
   `python -m venv .venv`
4. Activate it:
   PowerShell: `.\.venv\Scripts\Activate.ps1`
   CMD: `.venv\Scripts\activate.bat`
5. Install dependencies:
   `python -m pip install -r requirements.txt`
6. Run:
   `python -m streamlit run app.py`
7. The browser should open the dashboard. If not, open the local URL printed in the terminal, usually `http://localhost:8501`.

## Dataset upload
Use the sidebar's CSV uploader. The first version can automatically recognize common names for:
- machine / machine_id / machine_name / stage / process / workstation
- processing_time_min / processing_time / cycle_time_min / cycle_time
- utilization_pct / utilization
- downtime_min / downtime
- units_completed / output_units / units_produced

If your organizer CSV uses different names, inspect its columns first and adapt the column-name matching section in `app.py`. Never assume the sample column structure matches the real data.

## Suggested team split
Member A: inspect/clean dataset and validate the bottleneck logic.
Member B: run the dashboard, improve labels/layout, prepare pitch and demo.
Both: verify that every displayed claim is supported by the data.
