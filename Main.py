import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Streamlit app
st.title("Engine Datalog Analyzer")

# File upload
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
if uploaded_file is not None:
    # Load the CSV file and skip the first row (metadata)
    data = pd.read_csv(uploaded_file, skiprows=1)

    # Clean up column names
    data.columns = data.columns.str.strip()

    # Check for necessary columns
    required_columns = [
        "Time (s)",
        "Accelerator position (%)",
        "Boost Pressure (psi)",
        "Target Rail press (psi)",
        "Engine RPM (RPM)",
        "Ignition timing (DEG)",
        "Fuel Rail Pressure (bar)",
        "Wastegate valve position (%)"
    ]

    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        st.error(f"Missing columns in the uploaded file: {', '.join(missing_columns)}")
    else:
        # Detect wide-open throttle (WOT) conditions (Accelerator Position > 95%)
        wot_data = data[data["Accelerator position (%)"] > 95]

        st.subheader("Wide-Open Throttle Periods")
        st.write(wot_data)

        # Create dual-axis plot using Plotly subplots
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Plot for left y-axis (Boost Pressure, Target Rail Pressure, Engine RPM, Wastegate Position)
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Boost Pressure (psi)'],
                                 mode='lines', name='Boost Pressure (psi)', line=dict(color='blue')), secondary_y=False)
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Target Rail press (psi)'],
                                 mode='lines', name='Target Rail Pressure (psi)', line=dict(color='green')), secondary_y=False)
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Engine RPM (RPM)'],
                                 mode='lines', name='Engine RPM', line=dict(color='purple')), secondary_y=False)
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Wastegate valve position (%)'],
                                 mode='lines', name='Wastegate Valve Position (%)', line=dict(color='brown', dash='dash')), secondary_y=False)

        # Plot for right y-axis (Accelerator Position, Ignition Timing, Fuel Rail Pressure)
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Accelerator position (%)'],
                                 mode='lines', name='Accelerator Position (%)', line=dict(color='red')), secondary_y=True)
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Ignition timing (DEG)'],
                                 mode='lines', name='Ignition Timing (DEG)', line=dict(color='orange')), secondary_y=True)
        fig.add_trace(go.Scatter(x=wot_data['Time (s)'], y=wot_data['Fuel Rail Pressure (bar)'],
                                 mode='lines', name='Fuel Rail Pressure (bar)', line=dict(color='cyan')), secondary_y=True)

        # Update axis labels and layout
        fig.update_layout(
            title="Engine Parameters During Wide-Open Throttle (Dual Axis)",
            xaxis_title="Time (s)",
            yaxis=dict(title="Boost / Rail Pressure / RPM / Wastegate Position"),
            yaxis2=dict(title="Accelerator Position / Timing / Fuel Pressure", overlaying="y", side="right"),
            hovermode="x unified",
            height=700
        )

        # Display the interactive graph
        st.plotly_chart(fig)

        # Log Report Section
        st.subheader("Log Report")

        # Initialize report
        log_report = ""

        # 1. Peak Boost
        peak_boost = wot_data['Boost Pressure (psi)'].max()
        peak_boost_time = wot_data.loc[wot_data['Boost Pressure (psi)'].idxmax(), 'Time (s)']
        log_report += f"**Peak Boost Pressure:** {peak_boost} psi at {peak_boost_time} seconds.\n\n"

        # 2. Boost Curve Description
        boost_start = wot_data['Boost Pressure (psi)'].iloc[0]
        boost_end = wot_data['Boost Pressure (psi)'].iloc[-1]
        if boost_end > boost_start:
            boost_description = "Boost pressure increases steadily during WOT."
        elif boost_end < boost_start:
            boost_description = "Boost pressure decreases steadily during WOT."
        else:
            boost_description = "Boost pressure remains stable during WOT."
        log_report += f"**Boost Curve Description:** {boost_description}\n\n"

        # 3. Peak Timing
        peak_timing = wot_data['Ignition timing (DEG)'].max()
        peak_timing_time = wot_data.loc[wot_data['Ignition timing (DEG)'].idxmax(), 'Time (s)']
        log_report += f"**Peak Ignition Timing:** {peak_timing} degrees at {peak_timing_time} seconds.\n\n"

        # 4. Timing Smoothness
        timing_std = wot_data['Ignition timing (DEG)'].std()
        log_report += f"**Timing Smoothness:** Standard deviation of ignition timing is {timing_std:.2f} degrees.\n\n"

        # 5. Boost Smoothness
        boost_std = wot_data['Boost Pressure (psi)'].std()
        log_report += f"**Boost Smoothness:** Standard deviation of boost pressure is {boost_std:.2f} psi.\n\n"

        # 6. Fuel Pressure Drops
        fuel_pressure_issue = wot_data[abs(wot_data['Fuel Rail Pressure (bar)'] - wot_data['Target Rail press (psi)']) > 50]
        if not fuel_pressure_issue.empty:
            log_report += f"**Fuel Pressure Drops:** Significant drops detected at {fuel_pressure_issue['Time (s)'].tolist()} seconds.\n\n"

            # Snapshot of the issue
            st.subheader("Snapshot: Fuel Pressure Drops")
            fig_fuel_pressure = go.Figure()
            fig_fuel_pressure.add_trace(go.Scatter(x=fuel_pressure_issue['Time (s)'], y=fuel_pressure_issue['Fuel Rail Pressure (bar)'],
                                                   mode='lines', name='Fuel Rail Pressure (bar)', line=dict(color='cyan')))
            fig_fuel_pressure.update_layout(title="Fuel Pressure Drop Snapshot", xaxis_title="Time (s)", yaxis_title="Fuel Rail Pressure (bar)")
            st.plotly_chart(fig_fuel_pressure)
        else:
            log_report += "**Fuel Pressure Drops:** No significant drops detected.\n\n"

        # 7. Boost Pressure Fluctuations
        boost_fluctuations = wot_data[abs(wot_data['Boost Pressure (psi)'].diff()) > 3]
        if not boost_fluctuations.empty:
            log_report += f"**Boost Pressure Fluctuations:** Detected at {boost_fluctuations['Time (s)'].tolist()} seconds.\n\n"

            # Snapshot of the issue
            st.subheader("Snapshot: Boost Pressure Fluctuations")
            fig_fluct = go.Figure()
            fig_fluct.add_trace(go.Scatter(x=boost_fluctuations['Time (s)'], y=boost_fluctuations['Boost Pressure (psi)'],
                                           mode='lines', name='Boost Pressure (psi)', line=dict(color='blue')))
            fig_fluct.update_layout(title="Boost Pressure Fluctuation Snapshot", xaxis_title="Time (s)", yaxis_title="Boost Pressure (psi)")
            st.plotly_chart(fig_fluct)
        else:
            log_report += "**Boost Pressure Fluctuations:** No significant fluctuations detected.\n\n"

        # 8. Negative Timing Deviations
        negative_timing = wot_data[wot_data['Ignition timing (DEG)'] < 0]
        if not negative_timing.empty:
            log_report += f"**Negative Timing Deviations:** Detected at {negative_timing['Time (s)'].tolist()} seconds.\n\n"

            # Snapshot of the issue
            st.subheader("Snapshot: Negative Timing Deviation")
            fig_neg_timing = go.Figure()
            fig_neg_timing.add_trace(go.Scatter(x=negative_timing['Time (s)'], y=negative_timing['Ignition timing (DEG)'],
                                                mode='lines', name='Ignition Timing (DEG)', line=dict(color='orange')))
            fig_neg_timing.update_layout(title="Negative Timing Deviation Snapshot", xaxis_title="Time (s)", yaxis_title="Ignition Timing (DEG)")
            st.plotly_chart(fig_neg_timing)
        else:
            log_report += "**Negative Timing Deviations:** No negative timing detected.\n\n"

        # 9. Wastegate Valve Analysis
        # a. Wastegate at 0%
        wastegate_zero = wot_data[wot_data['Wastegate valve position (%)'] == 0]
        if not wastegate_zero.empty:
            log_report += f"**Wastegate at 0%:** Detected at {wastegate_zero['Time (s)'].tolist()} seconds.\n\n"

            # Snapshot of the issue
            st.subheader("Snapshot: Wastegate at 0%")
            fig_wg_zero = go.Figure()
            fig_wg_zero.add_trace(go.Scatter(x=wastegate_zero['Time (s)'], y=wastegate_zero['Wastegate valve position (%)'],
                                            mode='markers', name='Wastegate Valve Position (%)', marker=dict(color='brown', size=10)))
            fig_wg_zero.update_layout(title="Wastegate at 0% Snapshot", xaxis_title="Time (s)", yaxis_title="Wastegate Valve Position (%)")
            st.plotly_chart(fig_wg_zero)
        else:
            log_report += "**Wastegate at 0%:** No instances detected.\n\n"

        # b. Wastegate Fluctuations
        wastegate_fluctuations = wot_data[abs(wot_data['Wastegate valve position (%)'].diff()) > 5]
        if not wastegate_fluctuations.empty:
            log_report += f"**Wastegate Valve Fluctuations:** Detected at {wastegate_fluctuations['Time (s)'].tolist()} seconds.\n\n"

            # Snapshot of the issue
            st.subheader("Snapshot: Wastegate Valve Fluctuations")
            fig_wg_fluct = go.Figure()
            fig_wg_fluct.add_trace(go.Scatter(x=wastegate_fluctuations['Time (s)'], y=wastegate_fluctuations['Wastegate valve position (%)'],
                                              mode='lines+markers', name='Wastegate Valve Position (%)', line=dict(color='brown')))
            fig_wg_fluct.update_layout(title="Wastegate Valve Fluctuations Snapshot", xaxis_title="Time (s)", yaxis_title="Wastegate Valve Position (%)")
            st.plotly_chart(fig_wg_fluct)
        else:
            log_report += "**Wastegate Valve Fluctuations:** No significant fluctuations detected.\n\n"

        # Display the compiled report
        st.markdown(log_report)

        # Additional Summary
        st.subheader("Summary Statistics")
        summary_data = {
            "Metric": ["Peak Boost (psi)", "Peak Ignition Timing (DEG)", "Boost Pressure Std Dev (psi)",
                       "Ignition Timing Std Dev (DEG)", "Total Fuel Pressure Drops", "Total Boost Fluctuations",
                       "Total Wastegate at 0%", "Total Wastegate Fluctuations"],
            "Value": [
                peak_boost,
                peak_timing,
                round(boost_std, 2),
                round(timing_std, 2),
                len(fuel_pressure_issue),
                len(boost_fluctuations),
                len(wastegate_zero),
                len(wastegate_fluctuations)
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        st.table(summary_df)
