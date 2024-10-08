import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io

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
        if std_dev < 0.5:
            return "Very Smooth"
        elif std_dev < 1.5:
            return "Smooth"
        elif std_dev < 3:
            return "Somewhat Smooth"
        else:
            return "Not Smooth"
    elif data_type == 'timing':
        if std_dev < 0.5:
            return "Very Smooth"
        elif std_dev < 1.5:
            return "Smooth"
        elif std_dev < 3:
            return "Somewhat Smooth"
        else:
            return "Not Smooth"
    else:
        return "N/A"

# Function to rename duplicate columns by appending suffixes
def rename_duplicates(columns):
    seen = {}
    new_columns = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            new_col = f"{col}_{seen[col]}"
            new_columns.append(new_col)
        else:
            seen[col] = 1
            new_columns.append(col)
    return new_columns

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

            # Rename duplicate columns to ensure uniqueness
            data_standardized.columns = rename_duplicates(data_standardized.columns)

            # Initialize the log report
            log_report = ""

            # Detect wide-open throttle (WOT) conditions (Accelerator Position > 95%) if accelerator position is available
            if "Accelerator Position" in data_standardized.columns:
                wot_data = data_standardized[data_standardized["Accelerator Position"] > 95].copy()
                st.subheader("Wide-Open Throttle Periods")
                try:
                    st.write(wot_data)
                except Exception as e:
                    st.error(f"Error displaying WOT data: {e}")
            else:
                # If accelerator position is not available, consider entire dataset as WOT
                wot_data = data_standardized.copy()
                st.subheader("Dataset (Accelerator Position not detected, considering entire dataset)")
                try:
                    st.write(wot_data)
                except Exception as e:
                    st.error(f"Error displaying dataset: {e}")

            # Ensure 'Time' column exists
            if "Time" not in wot_data.columns:
                st.error("Time column is missing after mapping. Cannot proceed with plotting and analysis.")
            else:
                # Convert all relevant columns to numeric types
                numeric_columns = [col for col in wot_data.columns if col != "Time"]
                for col in numeric_columns:
                    wot_data[col] = pd.to_numeric(wot_data[col], errors='coerce')

                # Drop columns that are still non-numeric after conversion
                non_numeric_columns = wot_data.select_dtypes(include=['object']).columns.tolist()
                if non_numeric_columns:
                    st.warning(f"The following columns have non-numeric data and will be excluded from analysis and plotting: {', '.join(non_numeric_columns)}")
                    wot_data = wot_data.drop(columns=non_numeric_columns)

                # Remove duplicate 'Fuel Rail Pressure (psi)' if exists after renaming
                if wot_data.columns.duplicated().any():
                    dup_cols = wot_data.columns[wot_data.columns.duplicated()].unique().tolist()
                    st.warning(f"Duplicate columns detected after renaming: {', '.join(dup_cols)}. Only the first occurrence will be used.")
                    wot_data = wot_data.loc[:, ~wot_data.columns.duplicated()]

                # Calculate frame-to-frame differences for smoothness
                wot_data_sorted = wot_data.sort_values("Time").copy()  # Ensure data is sorted by Time and make a copy
                for col in numeric_columns:
                    if col != "Time":
                        wot_data_sorted.loc[:, f"{col}_diff"] = wot_data_sorted[col].diff().abs()

                # Smoothness Calculation based on rolling frame-to-frame deviations
                window_size = 5  # Adjust window size as needed
                boost_diff_col = "Boost Pressure_diff"
                timing_diff_col = "Ignition Timing_diff"

                if boost_diff_col in wot_data_sorted.columns:
                    boost_roll_std = wot_data_sorted[boost_diff_col].rolling(window=window_size, min_periods=1).std()
                    boost_smoothness = get_smoothness_score(boost_roll_std.mean(), data_type='boost')
                else:
                    boost_smoothness = "N/A"

                if timing_diff_col in wot_data_sorted.columns:
                    timing_roll_std = wot_data_sorted[timing_diff_col].rolling(window=window_size, min_periods=1).std()
                    timing_smoothness = get_smoothness_score(timing_roll_std.mean(), data_type='timing')
                else:
                    timing_smoothness = "N/A"

                # Plot Boost Pressure Over Time
                st.subheader("Boost Pressure Over Time")
                try:
                    fig_boost = go.Figure()
                    fig_boost.add_trace(go.Scatter(
                        x=wot_data_sorted["Time"],
                        y=wot_data_sorted["Boost Pressure"],
                        mode='lines',
                        name='Boost Pressure',
                        line=dict(color='blue')
                    ))
                    fig_boost.update_layout(
                        title="Boost Pressure Over Time",
                        xaxis_title="Time (s)",
                        yaxis_title="Boost Pressure (psi)",
                        hovermode="x unified",
                        height=500
                    )
                    st.plotly_chart(fig_boost)
                except Exception as e:
                    st.error(f"Error plotting Boost Pressure: {e}")

                # Timing Anomaly Detection
                st.subheader("Timing Anomaly Detection")
                try:
                    # Define a window to detect increase-decrease-increase pattern
                    timing = wot_data_sorted["Ignition Timing"]
                    timing_anomaly = False
                    anomaly_times = []

                    # Iterate through the data to find the pattern
                    for i in range(1, len(timing)-1):
                        if timing.iloc[i] < timing.iloc[i-1] and timing.iloc[i+1] > timing.iloc[i]:
                            timing_anomaly = True
                            anomaly_times.append(wot_data_sorted["Time"].iloc[i])

                    if timing_anomaly:
                        log_report += f"**Timing Anomalies Detected:** Occurred at {anomaly_times} seconds.\n\n"
                        st.success(f"Timing anomalies detected at {anomaly_times} seconds.")
                    else:
                        log_report += f"**Timing Anomalies:** No anomalies detected.\n\n"
                        st.info("No timing anomalies detected.")
                except Exception as e:
                    log_report += f"**Timing Anomaly Detection Error:** {e}\n\n"

                # Wastegate Valve Analysis
                st.subheader("Wastegate Valve Analysis")
                try:
                    if "Wastegate Valve Position" in wot_data_sorted.columns:
                        # Detect if wastegate valve is under 12% for an extended period (e.g., >5 consecutive readings)
                        threshold = 12
                        extended_period = 5  # Number of consecutive readings
                        wv = wot_data_sorted["Wastegate Valve Position"]

                        # Create a boolean series where True indicates valve position < threshold
                        wv_below_threshold = wv < threshold

                        # Identify consecutive periods
                        wv_below_threshold_shift = wv_below_threshold.shift(1, fill_value=False)
                        wv_group = (wv_below_threshold != wv_below_threshold_shift).cumsum()
                        wv_consecutive = wot_data_sorted.groupby(wv_group)["Wastegate Valve Position"].agg(['count', 'min'])

                        # Find groups where count >= extended_period and min < threshold
                        problematic_groups = wv_consecutive[(wv_consecutive['count'] >= extended_period) & (wv_consecutive['min'] < threshold)]

                        if not problematic_groups.empty:
                            anomaly_periods = []
                            for group in problematic_groups.index:
                                period = wot_data_sorted[wv_group == group]["Time"].tolist()
                                anomaly_periods.append(period)
                            log_report += f"**Wastegate Valve Issues Detected:** Valve remained below {threshold}% for extended periods at times: {anomaly_periods} seconds.\n\n"
                            st.error(f"Wastegate valve remained below {threshold}% for extended periods at times: {anomaly_periods} seconds.\nPotential boost leak or wastegate issue.")
                        else:
                            log_report += f"**Wastegate Valve Issues:** No extended periods below {threshold}% detected.\n\n"
                            st.success(f"No extended periods below {threshold}% detected for Wastegate Valve Position.")
                    else:
                        log_report += f"**Wastegate Valve Analysis:** Not available.\n\n"
                        st.info("Wastegate Valve Position data not available.")
                except Exception as e:
                    log_report += f"**Wastegate Valve Analysis Error:** {e}\n\n"

                # Fuel Pressure Drops Snapshot
                st.subheader("Snapshot: Fuel Pressure Drops")
                try:
                    if "Fuel Rail Pressure (psi)" in wot_data_sorted.columns and "Target Rail Pressure" in wot_data_sorted.columns:
                        fuel_pressure_psi = wot_data_sorted["Fuel Rail Pressure (psi)"]
                        target_pressure_psi = wot_data_sorted["Target Rail Pressure"]
                        pressure_diff = abs(fuel_pressure_psi - target_pressure_psi)
                        fuel_pressure_issue = wot_data_sorted[pressure_diff > 50]
                        if not fuel_pressure_issue.empty:
                            fig_fuel_pressure = go.Figure()
                            fig_fuel_pressure.add_trace(go.Scatter(
                                x=fuel_pressure_issue["Time"],
                                y=fuel_pressure_issue["Fuel Rail Pressure (psi)"],
                                mode='markers',
                                name='Fuel Rail Pressure (psi)',
                                marker=dict(color='cyan', size=8)
                            ))
                            fig_fuel_pressure.update_layout(
                                title="Fuel Pressure Drops Snapshot",
                                xaxis_title="Time (s)",
                                yaxis_title="Fuel Rail Pressure (psi)",
                                height=400
                            )
                            st.plotly_chart(fig_fuel_pressure)
                        else:
                            st.info("No significant Fuel Pressure drops detected.")
                    else:
                        st.info("Fuel Rail Pressure or Target Rail Pressure data not available.")
                except Exception as e:
                    st.error(f"Error generating Fuel Pressure Drops snapshot: {e}")

                # Log Report Section
                st.subheader("Log Report")
                st.markdown(log_report)

                # Summary Statistics
                st.subheader("Summary Statistics")
                summary_data = {
                    "Metric": [
                        "Peak Boost (psi)", 
                        "Peak Ignition Timing (DEG)", 
                        "Boost Smoothness", 
                        "Timing Smoothness", 
                        "Total Fuel Pressure Drops", 
                        "Total Timing Anomalies",
                        "Total Wastegate Issues"
                    ],
                    "Value": [
                        f"{wot_data_sorted['Boost Pressure'].max():.2f} psi" if "Boost Pressure" in wot_data_sorted.columns else "N/A",
                        f"{wot_data_sorted['Ignition Timing'].max():.2f} degrees" if "Ignition Timing" in wot_data_sorted.columns else "N/A",
                        boost_smoothness,
                        timing_smoothness,
                        len(fuel_pressure_issue) if ("Fuel Rail Pressure (psi)" in wot_data_sorted.columns and "Target Rail Pressure" in wot_data_sorted.columns) else "N/A",
                        len(anomaly_times) if 'anomaly_times' in locals() else "N/A",
                        len(anomaly_periods) if 'anomaly_periods' in locals() else "N/A"
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                st.table(summary_df)
else:
    st.info("Please upload a CSV file to begin analysis.")
