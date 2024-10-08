import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Streamlit app
st.title("Engine Datalog Analyzer")

# File upload
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
if uploaded_file is not None:
    # Load the CSV file and skip the first row (metadata)
    data = pd.read_csv(uploaded_file, skiprows=1)

    # Clean up column names
    data.columns = data.columns.str.strip()

    # Detect wide-open throttle (WOT) conditions (Accelerator Position > 95%)
    if "Accelerator position (%     )" in data.columns:
        wot_data = data[data["Accelerator position (%     )"] > 95]

        st.subheader("Wide-Open Throttle Periods")
        st.write(wot_data)

        # Plotting interactive graph with Plotly
        fig = go.Figure()

        # Add lines for each relevant engine parameter
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Boost Pressure (psi   )'], mode='lines', name='Boost Pressure (psi)'))
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Accelerator position (%     )'], mode='lines', name='Accelerator Position (%)'))
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Ignition timing (DEG   )'], mode='lines', name='Ignition Timing (DEG)'))
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Fuel Rail Pressure (bar   )'], mode='lines', name='Fuel Rail Pressure (bar)'))
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Target Rail press (psi   )'], mode='lines', name='Target Rail Pressure (psi)'))
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Wastegate valve position (%     )'], mode='lines', name='Wastegate Valve Position (%)'))

        # Customize layout
        fig.update_layout(
            title="Engine Parameters During Wide-Open Throttle",
            xaxis_title="Time (s)",
            yaxis_title="Values",
            hovermode="x unified"
        )

        # Display the interactive graph
        st.plotly_chart(fig)

        # Log Report Section
        st.subheader("Log Report")
        
        # Detect issues and create a report
        log_report = ""

        # Large boost pressure fluctuations
        boost_fluctuations = wot_data[abs(wot_data['Boost Pressure (psi   )'].diff()) > 3]
        if not boost_fluctuations.empty:
            log_report += f"Large Boost Pressure Fluctuations Detected at:\n{boost_fluctuations['Time (s)'].tolist()}\n\n"

        # Negative timing deviations
        negative_timing = wot_data[wot_data['Ignition timing (DEG   )'] < 0]
        if not negative_timing.empty:
            log_report += f"Negative Timing Deviations Detected at:\n{negative_timing['Time (s)'].tolist()}\n\n"

        # High wastegate valve percentage (close to 0%)
        high_wastegate = wot_data[wot_data['Wastegate valve position (%     )'] < 1]
        if not high_wastegate.empty:
            log_report += f"High Wastegate Valve Position (Close to 0%) Detected at:\n{high_wastegate['Time (s)'].tolist()}\n\n"

        # Fuel pressure collapse (when fuel pressure doesn't track target rail pressure)
        fuel_pressure_issue = wot_data[abs(wot_data['Fuel Rail Pressure (bar   )'] - wot_data['Target Rail press (psi   )']) > 50]
        if not fuel_pressure_issue.empty:
            log_report += f"Fuel Pressure Collapse Detected at:\n{fuel_pressure_issue['Time (s)'].tolist()}\n\n"

        if log_report:
            st.write(log_report)
        else:
            st.write("No significant issues detected during wide-open throttle.")
    else:
        st.error("Accelerator position column not found! Please check the uploaded file.")
