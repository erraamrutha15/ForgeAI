ForgeAI updated for the organizer-provided data_iare.csv

1. Extract this folder to your computer.
2. Install dependencies if needed: python -m pip install streamlit pandas matplotlib
3. Open PowerShell in this folder.
4. Run: python -m streamlit run app.py

The app reads data_iare.csv automatically when no upload is selected. It summarizes the dataset's supplied bottleneck_risk labels and numeric operational/sensor metrics. It does not train a forecasting model.
