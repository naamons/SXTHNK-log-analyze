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
        "fuel_rail_pressure": None,
        "wastegate_valve_position": None
    }

    for col in columns:
        col_lower = col.lower().replace(" ", "").replace("(", "").replace(")", "").replace("%", "percent").replace("_", "")
        if "time" in col_lower:
            mapping["time"] = col
        elif "accelerator" in col_lower and "position" in col_lower:
            mapping["accelerator_position"] = col
        elif "boost" in col_lower and "pressure" in col_lower:
            mapping["boost_pressure"] = col
        elif ("targetrail" in col_lower or "targetrailpressure" in col_lower or "target_rail_press" in col_lower):
            mapping["target_rail_pressure"] = col
        elif "rpm" in col_lower or "engine_rpm" in col_lower:
            mapping["engine_rpm"] = col
        elif ("ignition" in col_lower and "timing" in col_lower) or ("timingdeg" in col_lower):
            mapping["ignition_timing"] = col
        elif "fuelrail" in col_lower and "pressure" in col_lower:
            mapping["fuel_rail_pressure"] = col
        elif "wastegate" in col_lower and "position" in col_lower:
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
        essential_fields = ["time", "boost_pressure"]  # Define essential fields as needed
        missing_fields = [field.replace("_", " ").title() for field, col in column_mapping.items() if col is None and field in essential_fields]

        if missing_fields:
            st.error(f"Missing essential columns in the uploaded file: {', '.join(missing_fields)}")
        else:
            # Display mapped columns for debugging
            st.subheader("Detected Columns")
            detected_columns = {key: value for key, value in column_mapping.items() if value is not None}
            st.write(detected_columns)

            # Detect wide-open throttle (WOT) conditions (Accelerator Position > 95%) if accelerator position is available
            if column_mapping["accelerator_position"]:
                wot_data = data[data[column_mapping["accelerator_position"]] > 95]
                st.subheader("Wide-Open Throttle Periods")
                st.write(wot_data)
            else:
                # If accelerator position is not available, consider entire dataset as WOT
                wot_data = data.copy()
                st.subheader("Dataset (Accelerator Position not detected, considering entire dataset)")
                st.write(wot_data)

            # Create dynamic list of traces
            traces = []
            y_axis_assignments = {}
            for key, col in column_mapping.items():
                if col and col != column_mapping["time"]:
                    y_axis = assign_y_axis(col)
                    y_axis_assignments[col] = y_axis
                    traces.append({
                        "name": col,
                        "x": wot_data[column_mapping["time"]],
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
                "title": "Engine Parameters",
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
            st.plotly_chart(fig)

            # Log Report Section
            st.subheader("Log Report")

            # Initialize report
            log_report = ""

            # Example: Calculate and report peak boost if boost pressure is available
            if column_mapping["boost_pressure"]:
                peak_boost = wot_data[column_mapping["boost_pressure"]].max()
                peak_boost_time = wot_data.loc[wot_data[column_mapping["boost_pressure"]].idxmax(), column_mapping["time"]]
                log_report += f"**Peak Boost Pressure:** {peak_boost} psi at {peak_boost_time} seconds.\n\n"

                # Boost Smoothness
                boost_std = wot_data[column_mapping["boost_pressure"]].std()
                log_report += f"**Boost Smoothness:** Standard deviation of boost pressure is {boost_std:.2f} psi.\n\n"

            # Example: Peak Ignition Timing
            if column_mapping["ignition_timing"]:
                peak_timing = wot_data[column_mapping["ignition_timing"]].max()
                peak_timing_time = wot_data.loc[wot_data[column_mapping["ignition_timing"]].idxmax(), column_mapping["time"]]
                log_report += f"**Peak Ignition Timing:** {peak_timing} degrees at {peak_timing_time} seconds.\n\n"

                # Timing Smoothness
                timing_std = wot_data[column_mapping["ignition_timing"]].std()
                log_report += f"**Timing Smoothness:** Standard deviation of ignition timing is {timing_std:.2f} degrees.\n\n"

            # Example: Fuel Pressure Drops
            if column_mapping["fuel_rail_pressure"] and column_mapping["target_rail_pressure"]:
                # Assuming target rail pressure is in psi and fuel rail pressure is in bar, convert bar to psi if necessary
                # 1 bar ≈ 14.5038 psi
                fuel_pressure_psi = wot_data[column_mapping["fuel_rail_pressure"]] * 14.5038
                pressure_diff = abs(fuel_pressure_psi - wot_data[column_mapping["target_rail_pressure"]])
                fuel_pressure_issue = wot_data[pressure_diff > 50]
                if not fuel_pressure_issue.empty:
                    log_report += f"**Fuel Pressure Drops:** Significant drops detected at {fuel_pressure_issue[column_mapping['time']].tolist()} seconds.\n\n"
                else:
                    log_report += f"**Fuel Pressure Drops:** No significant drops detected.\n\n"

            # Example: Wastegate Valve Analysis
            if column_mapping["wastegate_valve_position"]:
                # Wastegate at 0%
                wastegate_zero = wot_data[wot_data[column_mapping["wastegate_valve_position"]] == 0]
                if not wastegate_zero.empty:
                    log_report += f"**Wastegate at 0%:** Detected at {wastegate_zero[column_mapping['time']].tolist()} seconds.\n\n"
                else:
                    log_report += f"**Wastegate at 0%:** No instances detected.\n\n"

                # Wastegate Fluctuations
                wastegate_fluctuations = wot_data[wot_data[column_mapping["wastegate_valve_position"]].diff().abs() > 5]
                if not wastegate_fluctuations.empty:
                    log_report += f"**Wastegate Valve Fluctuations:** Detected at {wastegate_fluctuations[column_mapping['time']].tolist()} seconds.\n\n"
                else:
                    log_report += f"**Wastegate Valve Fluctuations:** No significant fluctuations detected.\n\n"

            # Display the compiled report
            st.markdown(log_report)

            # Additional Summary (if needed)
            # You can add more summary statistics here based on available data

            # Dynamic Plotting: Plot all available data
            st.subheader("All Available Data Plots")
            dynamic_fig = make_subplots(specs=[[{"secondary_y": True}]]) if secondary_y else make_subplots()

            for key, col in column_mapping.items():
                if col and col != column_mapping["time"]:
                    y_axis = assign_y_axis(col)
                    if y_axis == 'left':
                        dynamic_fig.add_trace(go.Scatter(x=wot_data[column_mapping["time"]], y=wot_data[col],
                                                        mode='lines', name=col), secondary_y=False if secondary_y else None)
                    else:
                        dynamic_fig.add_trace(go.Scatter(x=wot_data[column_mapping["time"]], y=wot_data[col],
                                                        mode='lines', name=col), secondary_y=True)

            # Update dynamic figure layout
            dynamic_layout = {
                "title": "All Engine Parameters",
                "xaxis_title": "Time (s)",
                "hovermode": "x unified",
                "height": 700
            }

            if secondary_y:
                dynamic_layout.update({
                    "yaxis": {"title": "Primary Parameters"},
                    "yaxis2": {"title": "Secondary Parameters", "overlaying": "y", "side": "right"}
                })
            else:
                dynamic_layout.update({
                    "yaxis": {"title": "Parameters"}
                })

            dynamic_fig.update_layout(dynamic_layout)
            st.plotly_chart(dynamic_fig)

else:
    st.info("Please upload a CSV file to begin analysis.")
