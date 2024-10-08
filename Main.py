import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Function to map CSV columns to expected data fields based on keywords
def map_columns(columns):
    mapping = {
        "time": None,
        "accelerator_position": None,
        "boost_pressure": None,
        "target_rail_pressure": None,
        "engine_rpm": None,
        "ignition_timing": None,
        "fuel_rail_pressure_bar": None,
        "wastegate_valve_position": None
    }

    for col in columns:
        col_clean = col.lower().replace(" ", "").replace("(", "").replace(")", "").replace("%", "percent").replace("_", "")
        if "time" in col_clean:
            mapping["time"] = col
        elif "accelerator" in col_clean and "position" in col_clean:
            mapping["accelerator_position"] = col
        elif "boost" in col_clean and "pressure" in col_clean:
            mapping["boost_pressure"] = col
        elif ("targetrail" in col_clean or "targetrailpressure" in col_clean or "targetrailpress" in col_clean):
            mapping["target_rail_pressure"] = col
        elif "rpm" in col_clean or "enginerpm" in col_clean:
            mapping["engine_rpm"] = col
        elif ("ignition" in col_clean and "timing" in col_clean) or ("timingdeg" in col_clean):
            mapping["ignition_timing"] = col
        elif "fuelrail" in col_clean and "pressure" in col_clean:
            mapping["fuel_rail_pressure_bar"] = col
        elif "wastegate" in col_clean and "position" in col_clean:
            mapping["wastegate_valve_position"] = col

    return mapping

# Function to assign y-axis based on data type
def assign_y_axis(column_name):
    percentage_keywords = ['accelerator', 'wastegate']
    rpm_keywords = ['rpm']
    timing_keywords = ['timing']
    pressure_keywords = ['boost', 'rail', 'fuel']

    col_lower = column_name.lower()
    if any(keyword in col_lower for keyword in percentage_keywords):
        return 'left'
    elif any(keyword in col_lower for keyword in rpm_keywords):
        return 'left'
    elif any(keyword in col_lower for keyword in timing_keywords):
        return 'right'
    elif any(keyword in col_lower for keyword in pressure_keywords):
        return 'left'
    else:
        return 'left'  # Default to left if uncertain

# Function to convert Fuel Rail Pressure from bar to psi
def convert_bar_to_psi(df, col_name):
    return df[col_name] * 14.5038

# Function to convert smoothness standard deviation to descriptive scores
def get_smoothness_score(std_dev, data_type='boost'):
    """
    Define threshold ranges for smoothness descriptors.
    Adjust these thresholds based on your specific data characteristics.
    """
    if data_type == 'boost':
        if std_dev < 1:
            return "Very Smooth"
        elif std_dev < 3:
            return "Smooth"
        elif std_dev < 5:
            return "Somewhat Smooth"
        else:
            return "Not Smooth"
    elif data_type == 'timing':
        if std_dev < 1:
            return "Very Smooth"
        elif std_dev < 3:
            return "Smooth"
        elif std_dev < 5:
            return "Somewhat Smooth"
        else:
            return "Not Smooth"
    else:
        return "N/A"

# Streamlit app
st.title("Engine Datalog Analyzer")

# File upload
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
if uploaded_file is not None:
    try:
        # Load the CSV file and skip the first row (metadata)
        data = pd.read_csv(uploaded_file, skiprows=1)
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
    else:
        # Clean up column names
        data.columns = data.columns.str.strip()

        # Map columns based on keywords
        column_mapping = map_columns(data.columns)

        # Identify missing essential columns
        essential_fields = ["time", "boost_pressure"]
        missing_fields = [field.replace("_", " ").title() for field, col in column_mapping.items() if col is None and field in essential_fields]

        if missing_fields:
            st.error(f"Missing essential columns in the uploaded file: {', '.join(missing_fields)}")
        else:
            # Display mapped columns for debugging
            st.subheader("Detected Columns and Standardized Names")
            standardized_mapping = {}
            for key, col in column_mapping.items():
                if col:
                    standardized_name = key.replace("_", " ").title()
                    if key == "fuel_rail_pressure_bar":
                        standardized_name = "Fuel Rail Pressure (bar)"
                    standardized_mapping[standardized_name] = col
            st.write(standardized_mapping)

            # Convert Fuel Rail Pressure from bar to psi if present
            if column_mapping["fuel_rail_pressure_bar"]:
                data["Fuel Rail Pressure (psi)"] = convert_bar_to_psi(data, column_mapping["fuel_rail_pressure_bar"])

            # Create a standardized DataFrame with standardized column names
            standardized_columns = {}
            for key, col in column_mapping.items():
                if col:
                    if key == "fuel_rail_pressure_bar":
                        standardized_columns[col] = "Fuel Rail Pressure (psi)"
                    else:
                        standardized_columns[col] = key.replace("_", " ").title()
            data_standardized = data.rename(columns=standardized_columns)

            # Detect wide-open throttle (WOT) conditions (Accelerator Position > 95%) if accelerator position is available
            if "Accelerator Position" in data_standardized.columns:
                wot_data = data_standardized[data_standardized["Accelerator Position"] > 95]
                st.subheader("Wide-Open Throttle Periods")
                st.write(wot_data)
            else:
                # If accelerator position is not available, consider entire dataset as WOT
                wot_data = data_standardized.copy()
                st.subheader("Dataset (Accelerator Position not detected, considering entire dataset)")
                st.write(wot_data)

            # Ensure 'Time' column exists
            if "Time" not in wot_data.columns:
                st.error("Time column is missing after mapping. Cannot proceed with plotting and analysis.")
            else:
                # Convert all relevant columns to numeric types
                numeric_columns = [col for col in wot_data.columns if col != "Time"]
                for col in numeric_columns:
                    wot_data[col] = pd.to_numeric(wot_data[col], errors='coerce')

                # Display DataFrame info for debugging
                st.subheader("DataFrame Information")
                buffer = io.StringIO()
                wot_data.info(buf=buffer)
                s = buffer.getvalue()
                st.text(s)

                # Display a sample of the DataFrame
                st.subheader("Data Sample")
                st.write(wot_data.head())

                # Create dynamic list of traces
                traces = []
                y_axis_assignments = {}
                for col in wot_data.columns:
                    if col != "Time":
                        y_axis = assign_y_axis(col)
                        y_axis_assignments[col] = y_axis
                        traces.append({
                            "name": col,
                            "x": wot_data["Time"],
                            "y": wot_data[col],
                            "type": "scatter",
                            "mode": "lines",
                            "yaxis": "y" if y_axis == 'left' else "y2",
                            "line": {"width": 2}
                        })

                # Determine if a secondary y-axis is needed
                secondary_y = any(y_axis_assignments[col] == 'right' for col in y_axis_assignments)

                # Create subplot figure
                if secondary_y:
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                else:
                    fig = make_subplots()

                # Add traces to the figure
                for trace in traces:
                    if trace["yaxis"] == "y":
                        fig.add_trace(go.Scatter(x=trace["x"], y=trace["y"], mode=trace["mode"],
                                                 name=trace["name"], line=trace["line"]), secondary_y=False if secondary_y else None)
                    else:
                        fig.add_trace(go.Scatter(x=trace["x"], y=trace["y"], mode=trace["mode"],
                                                 name=trace["name"], line=trace["line"]), secondary_y=True)

                # Update layout
                layout_dict = {
                    "title": "Engine Parameters During Wide-Open Throttle (Dual Axis)",
                    "xaxis_title": "Time (s)",
                    "hovermode": "x unified",
                    "height": 700
                }

                if secondary_y:
                    layout_dict.update({
                        "yaxis": {"title": "Primary Parameters"},
                        "yaxis2": {"title": "Secondary Parameters", "overlaying": "y", "side": "right"}
                    })
                else:
                    layout_dict.update({
                        "yaxis": {"title": "Parameters"}
                    })

                fig.update_layout(layout_dict)

                # Display the interactive graph
                try:
                    st.plotly_chart(fig)
                except Exception as e:
                    st.error(f"Error plotting Engine Parameters: {e}")

                # Log Report Section
                st.subheader("Log Report")

                # Initialize report
                log_report = ""

                # 1. Peak Boost
                if "Boost Pressure" in wot_data.columns:
                    try:
                        peak_boost = wot_data["Boost Pressure"].max()
                        peak_boost_time = wot_data.loc[wot_data["Boost Pressure"].idxmax(), "Time"]
                        log_report += f"**Peak Boost Pressure:** {peak_boost:.2f} psi at {peak_boost_time} seconds.\n\n"

                        # Boost Smoothness
                        boost_std = wot_data["Boost Pressure"].std()
                        boost_smoothness = get_smoothness_score(boost_std, data_type='boost')
                        log_report += f"**Boost Smoothness:** {boost_smoothness} (Std Dev: {boost_std:.2f} psi).\n\n"
                    except Exception as e:
                        log_report += f"**Boost Pressure Analysis Error:** {e}\n\n"
                else:
                    log_report += f"**Boost Pressure:** Not available.\n\n"

                # 2. Boost Curve Description
                if "Boost Pressure" in wot_data.columns:
                    try:
                        boost_start = wot_data["Boost Pressure"].iloc[0]
                        boost_end = wot_data["Boost Pressure"].iloc[-1]
                        if boost_end > boost_start:
                            boost_description = "Boost pressure increases steadily during WOT."
                        elif boost_end < boost_start:
                            boost_description = "Boost pressure decreases steadily during WOT."
                        else:
                            boost_description = "Boost pressure remains stable during WOT."
                        log_report += f"**Boost Curve Description:** {boost_description}\n\n"
                    except Exception as e:
                        log_report += f"**Boost Curve Description Error:** {e}\n\n"
                else:
                    log_report += f"**Boost Curve Description:** Not available.\n\n"

                # 3. Peak Ignition Timing
                if "Ignition Timing" in wot_data.columns:
                    try:
                        peak_timing = wot_data["Ignition Timing"].max()
                        peak_timing_time = wot_data.loc[wot_data["Ignition Timing"].idxmax(), "Time"]
                        log_report += f"**Peak Ignition Timing:** {peak_timing:.2f} degrees at {peak_timing_time} seconds.\n\n"

                        # Timing Smoothness
                        timing_std = wot_data["Ignition Timing"].std()
                        timing_smoothness = get_smoothness_score(timing_std, data_type='timing')
                        log_report += f"**Timing Smoothness:** {timing_smoothness} (Std Dev: {timing_std:.2f} degrees).\n\n"
                    except Exception as e:
                        log_report += f"**Ignition Timing Analysis Error:** {e}\n\n"
                else:
                    log_report += f"**Ignition Timing:** Not available.\n\n"

                # 4. Fuel Pressure Drops
                if "Fuel Rail Pressure (psi)" in wot_data.columns and "Target Rail Pressure" in wot_data.columns:
                    try:
                        fuel_pressure_psi = wot_data["Fuel Rail Pressure (psi)"]
                        target_pressure_psi = wot_data["Target Rail Pressure"]
                        pressure_diff = abs(fuel_pressure_psi - target_pressure_psi)
                        fuel_pressure_issue = wot_data[pressure_diff > 50]
                        if not fuel_pressure_issue.empty:
                            log_report += f"**Fuel Pressure Drops:** Significant drops detected at {fuel_pressure_issue['Time'].tolist()} seconds.\n\n"

                            # Snapshot of the issue
                            st.subheader("Snapshot: Fuel Pressure Drops")
                            fig_fuel_pressure = go.Figure()
                            fig_fuel_pressure.add_trace(go.Scatter(
                                x=fuel_pressure_issue["Time"],
                                y=fuel_pressure_issue["Fuel Rail Pressure (psi)"],
                                mode='lines+markers',
                                name='Fuel Rail Pressure (psi)',
                                line=dict(color='cyan')
                            ))
                            fig_fuel_pressure.update_layout(
                                title="Fuel Pressure Drop Snapshot",
                                xaxis_title="Time (s)",
                                yaxis_title="Fuel Rail Pressure (psi)"
                            )
                            st.plotly_chart(fig_fuel_pressure)
                        else:
                            log_report += f"**Fuel Pressure Drops:** No significant drops detected.\n\n"
                    except Exception as e:
                        log_report += f"**Fuel Pressure Drops Analysis Error:** {e}\n\n"
                else:
                    log_report += f"**Fuel Pressure Drops:** Not available.\n\n"

                # 5. Boost Pressure Fluctuations
                if "Boost Pressure" in wot_data.columns:
                    try:
                        boost_fluctuations = wot_data[wot_data["Boost Pressure"].diff().abs() > 3]
                        if not boost_fluctuations.empty:
                            log_report += f"**Boost Pressure Fluctuations:** Detected at {boost_fluctuations['Time'].tolist()} seconds.\n\n"

                            # Snapshot of the issue
                            st.subheader("Snapshot: Boost Pressure Fluctuations")
                            fig_fluct = go.Figure()
                            fig_fluct.add_trace(go.Scatter(
                                x=boost_fluctuations["Time"],
                                y=boost_fluctuations["Boost Pressure"],
                                mode='lines+markers',
                                name='Boost Pressure',
                                line=dict(color='blue')
                            ))
                            fig_fluct.update_layout(
                                title="Boost Pressure Fluctuation Snapshot",
                                xaxis_title="Time (s)",
                                yaxis_title="Boost Pressure (psi)"
                            )
                            st.plotly_chart(fig_fluct)
                        else:
                            log_report += f"**Boost Pressure Fluctuations:** No significant fluctuations detected.\n\n"
                    except Exception as e:
                        log_report += f"**Boost Pressure Fluctuations Analysis Error:** {e}\n\n"
                else:
                    log_report += f"**Boost Pressure Fluctuations:** Not available.\n\n"

                # 6. Negative Timing Deviations
                if "Ignition Timing" in wot_data.columns:
                    try:
                        negative_timing = wot_data[wot_data["Ignition Timing"] < 0]
                        if not negative_timing.empty:
                            log_report += f"**Negative Timing Deviations:** Detected at {negative_timing['Time'].tolist()} seconds.\n\n"

                            # Snapshot of the issue
                            st.subheader("Snapshot: Negative Timing Deviation")
                            fig_neg_timing = go.Figure()
                            fig_neg_timing.add_trace(go.Scatter(
                                x=negative_timing["Time"],
                                y=negative_timing["Ignition Timing"],
                                mode='lines+markers',
                                name='Ignition Timing (DEG)',
                                line=dict(color='orange')
                            ))
                            fig_neg_timing.update_layout(
                                title="Negative Timing Deviation Snapshot",
                                xaxis_title="Time (s)",
                                yaxis_title="Ignition Timing (DEG)"
                            )
                            st.plotly_chart(fig_neg_timing)
                        else:
                            log_report += f"**Negative Timing Deviations:** No negative timing detected.\n\n"
                    except Exception as e:
                        log_report += f"**Negative Timing Deviations Analysis Error:** {e}\n\n"
                else:
                    log_report += f"**Negative Timing Deviations:** Not available.\n\n"

                # 7. Wastegate Valve Analysis
                if "Wastegate Valve Position" in wot_data.columns:
                    try:
                        # a. Wastegate at 0%
                        wastegate_zero = wot_data[wot_data["Wastegate Valve Position"] == 0]
                        if not wastegate_zero.empty:
                            log_report += f"**Wastegate at 0%:** Detected at {wastegate_zero['Time'].tolist()} seconds.\n\n"

                            # Snapshot of the issue
                            st.subheader("Snapshot: Wastegate at 0%")
                            fig_wg_zero = go.Figure()
                            fig_wg_zero.add_trace(go.Scatter(
                                x=wastegate_zero["Time"],
                                y=wastegate_zero["Wastegate Valve Position"],
                                mode='markers',
                                name='Wastegate Valve Position (%)',
                                marker=dict(color='brown', size=10)
                            ))
                            fig_wg_zero.update_layout(
                                title="Wastegate at 0% Snapshot",
                                xaxis_title="Time (s)",
                                yaxis_title="Wastegate Valve Position (%)"
                            )
                            st.plotly_chart(fig_wg_zero)
                        else:
                            log_report += f"**Wastegate at 0%:** No instances detected.\n\n"

                        # b. Wastegate Fluctuations
                        wastegate_fluctuations = wot_data[wot_data["Wastegate Valve Position"].diff().abs() > 5]
                        if not wastegate_fluctuations.empty:
                            log_report += f"**Wastegate Valve Fluctuations:** Detected at {wastegate_fluctuations['Time'].tolist()} seconds.\n\n"

                            # Snapshot of the issue
                            st.subheader("Snapshot: Wastegate Valve Fluctuations")
                            fig_wg_fluct = go.Figure()
                            fig_wg_fluct.add_trace(go.Scatter(
                                x=wastegate_fluctuations["Time"],
                                y=wastegate_fluctuations["Wastegate Valve Position"],
                                mode='lines+markers',
                                name='Wastegate Valve Position (%)',
                                line=dict(color='brown')
                            ))
                            fig_wg_fluct.update_layout(
                                title="Wastegate Valve Fluctuations Snapshot",
                                xaxis_title="Time (s)",
                                yaxis_title="Wastegate Valve Position (%)"
                            )
                            st.plotly_chart(fig_wg_fluct)
                        else:
                            log_report += f"**Wastegate Valve Fluctuations:** No significant fluctuations detected.\n\n"
                    except Exception as e:
                        log_report += f"**Wastegate Valve Analysis Error:** {e}\n\n"
                else:
                    log_report += f"**Wastegate Valve Analysis:** Not available.\n\n"

                # Display the compiled report
                st.markdown(log_report)

                # Additional Summary
                st.subheader("Summary Statistics")
                summary_data = {
                    "Metric": [
                        "Peak Boost (psi)", 
                        "Peak Ignition Timing (DEG)", 
                        "Boost Smoothness", 
                        "Timing Smoothness", 
                        "Total Fuel Pressure Drops", 
                        "Total Boost Fluctuations",
                        "Total Wastegate at 0%", 
                        "Total Wastegate Fluctuations"
                    ],
                    "Value": [
                        f"{peak_boost:.2f} psi" if "Boost Pressure" in wot_data.columns else "N/A",
                        f"{peak_timing:.2f} degrees" if "Ignition Timing" in wot_data.columns else "N/A",
                        boost_smoothness if "Boost Pressure" in wot_data.columns else "N/A",
                        timing_smoothness if "Ignition Timing" in wot_data.columns else "N/A",
                        len(fuel_pressure_issue) if ("Fuel Rail Pressure (psi)" in wot_data.columns and "Target Rail Pressure" in wot_data.columns) else "N/A",
                        len(boost_fluctuations) if "Boost Pressure" in wot_data.columns else "N/A",
                        len(wastegate_zero) if "Wastegate Valve Position" in wot_data.columns else "N/A",
                        len(wastegate_fluctuations) if "Wastegate Valve Position" in wot_data.columns else "N/A"
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                st.table(summary_df)

                # Dynamic Plotting: Plot all available data
                st.subheader("All Engine Parameters")

                # Create dynamic list of traces for All Engine Parameters plot
                all_traces = []
                all_y_axis_assignments = {}
                for col in wot_data.columns:
                    if col != "Time":
                        y_axis = assign_y_axis(col)
                        all_y_axis_assignments[col] = y_axis
                        all_traces.append({
                            "name": col,
                            "x": wot_data["Time"],
                            "y": wot_data[col],
                            "type": "scatter",
                            "mode": "lines",
                            "yaxis": "y" if y_axis == 'left' else "y2",
                            "line": {"width": 2}
                        })

                # Determine if a secondary y-axis is needed
                all_secondary_y = any(all_y_axis_assignments[col] == 'right' for col in all_y_axis_assignments)

                # Create subplot figure for All Engine Parameters
                if all_secondary_y:
                    all_fig = make_subplots(specs=[[{"secondary_y": True}]])
                else:
                    all_fig = make_subplots()

                # Add all traces to the figure
                for trace in all_traces:
                    if trace["yaxis"] == "y":
                        all_fig.add_trace(go.Scatter(x=trace["x"], y=trace["y"], mode=trace["mode"],
                                                     name=trace["name"], line=trace["line"]), secondary_y=False if all_secondary_y else None)
                    else:
                        all_fig.add_trace(go.Scatter(x=trace["x"], y=trace["y"], mode=trace["mode"],
                                                     name=trace["name"], line=trace["line"]), secondary_y=True)

                # Update layout for All Engine Parameters plot
                all_layout_dict = {
                    "title": "All Engine Parameters",
                    "xaxis_title": "Time (s)",
                    "hovermode": "x unified",
                    "height": 700
                }

                if all_secondary_y:
                    all_layout_dict.update({
                        "yaxis": {"title": "Primary Parameters"},
                        "yaxis2": {"title": "Secondary Parameters", "overlaying": "y", "side": "right"}
                    })
                else:
                    all_layout_dict.update({
                        "yaxis": {"title": "Parameters"}
                    })

                all_fig.update_layout(all_layout_dict)

                # Display the All Engine Parameters plot
                try:
                    st.plotly_chart(all_fig)
                except Exception as e:
                    st.error(f"Error plotting All Engine Parameters: {e}")

else:
    st.info("Please upload a CSV file to begin analysis.")
