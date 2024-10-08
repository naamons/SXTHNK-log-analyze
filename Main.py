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

        # Plotting dual-axis graph with Plotly
        fig = go.Figure()

        # Add lines for Boost Pressure, Target Rail Pressure, and Engine RPM (left axis)
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Boost Pressure (psi   )'], 
                                 mode='lines', name='Boost Pressure (psi)', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Target Rail press (psi   )'], 
                                 mode='lines', name='Target Rail Pressure (psi)', line=dict(color='green')))
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Engine RPM (RPM   )'], 
                                 mode='lines', name='Engine RPM', line=dict(color='purple')))

        # Add lines for Accelerator Position, Ignition Timing, and Fuel Rail Pressure (right axis)
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Accelerator position (%     )'], 
                                 mode='lines', name='Accelerator Position (%)', line=dict(color='red'), yaxis='y2'))
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Ignition timing (DEG   )'], 
                                 mode='lines', name='Ignition Timing (DEG)', line=dict(color='orange'), yaxis='y2'))
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Fuel Rail Pressure (bar   )'], 
                                 mode='lines', name='Fuel Rail Pressure (bar)', line=dict(color='cyan'), yaxis='y2'))

        # Update layout for dual-axis
        fig.update_layout(
            title="Engine Parameters During Wide-Open Throttle (Dual Axis)",
            xaxis_title="Time (s)",
            yaxis=dict(title="Boost / Rail Pressure / Engine RPM", titlefont=dict(color="blue")),
            yaxis2=dict(title="Accelerator Position / Timing / Fuel Pressure", titlefont=dict(color="red"),
                        overlaying='y', side='right'),
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

            # Snapshot of the issue
            st.subheader("Snapshot: Large Boost Fluctuation")
            fig_fluct = go.Figure()
            fig_fluct.add_trace(go.Scatter(x=boost_fluctuations['Time (s)'], y=boost_fluctuations['Boost Pressure (psi   )'],
                                           mode='lines', name='Boost Pressure (psi)', line=dict(color='blue')))
            fig_fluct.update_layout(title="Boost Pressure Fluctuation Snapshot", xaxis_title="Time (s)", yaxis_title="Boost Pressure (psi)")
            st.plotly_chart(fig_fluct)

        # Negative timing deviations
        negative_timing = wot_data[wot_data['Ignition timing (DEG   )'] < 0]
        if not negative_timing.empty:
            log_report += f"Negative Timing Deviations Detected at:\n{negative_timing['Time (s)'].tolist()}\n\n"

            # Snapshot of the issue
            st.subheader("Snapshot: Negative Timing Deviation")
            fig_neg_timing = go.Figure()
            fig_neg_timing.add_trace(go.Scatter(x=negative_timing['Time (s)'], y=negative_timing['Ignition timing (DEG   )'],
                                                mode='lines', name='Ignition Timing (DEG)', line=dict(color='orange')))
            fig_neg_timing.update_layout(title="Negative Timing Deviation Snapshot", xaxis_title="Time (s)", yaxis_title="Ignition Timing (DEG)")
            st.plotly_chart(fig_neg_timing)

        # High wastegate valve percentage (close to 0%)
        high_wastegate = wot_data[wot_data['Wastegate valve position (%     )'] < 1]
        if not high_wastegate.empty:
            log_report += f"High Wastegate Valve Position (Close to 0%) Detected at:\n{high_wastegate['Time (s)'].tolist()}\n\n"

            # Snapshot of the issue
            st.subheader("Snapshot: High Wastegate Valve")
            fig_high_wastegate = go.Figure()
            fig_high_wastegate.add_trace(go.Scatter(x=high_wastegate['Time (s)'], y=high_wastegate['Wastegate valve position (%     )'],
                                                    mode='lines', name='Wastegate Valve Position (%)', line=dict(color='green')))
            fig_high_wastegate.update_layout(title="High Wastegate Valve Snapshot", xaxis_title="Time (s)", yaxis_title="Wastegate Valve Position (%)")
            st.plotly_chart(fig_high_wastegate)

        # Fuel pressure collapse (when fuel pressure doesn't track target rail pressure)
        fuel_pressure_issue = wot_data[abs(wot_data['Fuel Rail Pressure (bar   )'] - wot_data['Target Rail press (psi   )']) > 50]
        if not fuel_pressure_issue.empty:
            log_report += f"Fuel Pressure Collapse Detected at:\n{fuel_pressure_issue['Time (s)'].tolist()}\n\n"

            # Snapshot of the issue
            st.subheader("Snapshot: Fuel Pressure Collapse")
            fig_fuel_pressure = go.Figure()
            fig_fuel_pressure.add_trace(go.Scatter(x=fuel_pressure_issue['Time (s)'], y=fuel_pressure_issue['Fuel Rail Pressure (bar   )'],
                                                   mode='lines', name='Fuel Rail Pressure (bar)', line=dict(color='cyan')))
            fig_fuel_pressure.update_layout(title="Fuel Pressure Collapse Snapshot", xaxis_title="Time (s)", yaxis_title="Fuel Rail Pressure (bar)")
            st.plotly_chart(fig_fuel_pressure)

        if log_report:
            st.write(log_report)
        else:
            st.write("No significant issues detected during wide-open throttle.")
    else:
        st.error("Accelerator position column not found! Please check the uploaded file.")
