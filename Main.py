import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Streamlit app
st.title("Engine Datalog Analyzer")

# File upload
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
if uploaded_file is not None:
    # Load the CSV data
    data = pd.read_csv(uploaded_file)

    # Display the raw column names for inspection
    st.write("Raw Column Names:", list(data.columns))

    # Clean up column names by stripping leading/trailing spaces
    data.columns = data.columns.str.strip()

    # Display the cleaned column names for further inspection
    st.write("Cleaned Column Names:", list(data.columns))

    # Check if 'Accelerator position' is in the column names after cleaning
    if "Accelerator position (%     )" in data.columns:
        # Detect full-throttle conditions (Accelerator Position > 95%)
        full_throttle_data = data[data["Accelerator position (%     )"] > 95]

        st.subheader("Full Throttle Events")
        st.write(full_throttle_data)
    else:
        st.error("Accelerator position column not found! Please check column names above.")

    # Plot each column over time
    st.subheader("Graphs of all engine parameters over time")

    # Function to plot each parameter
    def plot_parameter(y_column, y_label):
        fig, ax = plt.subplots()
        ax.plot(data['Time (s)'], data[y_column])
        ax.set_xlabel('Time (s)')
        ax.set_ylabel(y_label)
        ax.set_title(f'{y_label} over time')
        st.pyplot(fig)

    # Plot individual engine parameters if columns exist
    if 'Boost Pressure (psi   )' in data.columns:
        plot_parameter('Boost Pressure (psi   )', 'Boost Pressure (psi)')
    if 'Wastegate valve position (%     )' in data.columns:
        plot_parameter('Wastegate valve position (%     )', 'Wastegate Valve Position (%)')
    if 'Fuel Rail Pressure (bar   )' in data.columns:
        plot_parameter('Fuel Rail Pressure (bar   )', 'Fuel Rail Pressure (bar)')
    if 'Target Rail press (psi   )' in data.columns:
        plot_parameter('Target Rail press (psi   )', 'Target Rail Pressure (psi)')
    if 'Accelerator position (%     )' in data.columns:
        plot_parameter('Accelerator position (%     )', 'Accelerator Position (%)')
    if 'Ignition timing (DEG   )' in data.columns:
        plot_parameter('Ignition timing (DEG   )', 'Ignition Timing (DEG)')
    if 'Engine RPM (RPM   )' in data.columns:
        plot_parameter('Engine RPM (RPM   )', 'Engine RPM')
    if 'Intake Air Temperature (`F    )' in data.columns:
        plot_parameter('Intake Air Temperature (`F    )', 'Intake Air Temperature (F)')

    # Calculate Boost Stability Score
    if 'Boost Pressure (psi   )' in data.columns:
        data['Boost StdDev'] = data['Boost Pressure (psi   )'].rolling(window=10).std()
        boost_stability_score = 1 / (1 + data['Boost StdDev'].mean())
        st.subheader("Boost Stability Score")
        st.write(f"Boost Stability Score: {boost_stability_score:.2f}")

    # Calculate Timing Stability Score
    if 'Ignition timing (DEG   )' in data.columns:
        data['Timing StdDev'] = data['Ignition timing (DEG   )'].rolling(window=10).std()
        timing_stability_score = 1 / (1 + data['Timing StdDev'].mean())
        st.subheader("Timing Stability Score")
        st.write(f"Timing Stability Score: {timing_stability_score:.2f}")

    # Detection logic for large boost pressure fluctuations
    if 'Boost Pressure (psi   )' in data.columns:
        boost_fluctuations = data[abs(data['Boost Pressure (psi   )'].diff()) > 3]
        st.subheader("Large Boost Pressure Fluctuations")
        st.write(boost_fluctuations)

    # Detecting negative timing deviations
    if 'Ignition timing (DEG   )' in data.columns:
        negative_timing = data[data['Ignition timing (DEG   )'] < 0]
        st.subheader("Negative Timing Deviations")
        st.write(negative_timing)

    # Detect high wastegate valve percentage (close to 0%)
    if 'Wastegate valve position (%     )' in data.columns:
        high_wastegate = data[data['Wastegate valve position (%     )'] < 1]
        st.subheader("High Wastegate Valve Position (Close to 0%)")
        st.write(high_wastegate)

    # Detect fuel pressure collapse (when fuel pressure doesn't track target rail pressure)
    if 'Fuel Rail Pressure (bar   )' in data.columns and 'Target Rail press (psi   )' in data.columns:
        fuel_pressure_issue = data[abs(data['Fuel Rail Pressure (bar   )'] - data['Target Rail press (psi   )']) > 50]
        st.subheader("Fuel Pressure Collapses or Deviation")
        st.write(fuel_pressure_issue)
    
