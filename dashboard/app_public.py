from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="PeoplePulse HR Analytics",
    page_icon="HR",
    layout="wide"
)

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "demo_package"

st.title("PeoplePulse | HR Analytics Command Center")
st.caption("Workforce attrition, attendance, hiring, productivity and planning")

st.info(
    "DEMO DATA NOTICE: The employee baseline uses the IBM HR Analytics "
    "dataset. Attendance, hiring, productivity and workforce event records "
    "are simulated demonstration data, not verified company records. "
    "Do not use these figures for actual HR decisions."
)


@st.cache_data
def load_csv(filename):
    path = DATA / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)



def get_dataset(session_key, filename):
    """Use uploaded data when available; otherwise load the default CSV."""
    uploaded_df = st.session_state.get(session_key)

    if uploaded_df is not None:
        return uploaded_df.copy(), "Uploaded dataset"

    return load_csv(filename), f"{filename} (default source)"


# Load default datasets

# --------------------------------------------------
# LOAD DEFAULT DATASETS OR THE SHARED UPLOAD
# --------------------------------------------------

employees = load_csv("employees.csv")
attendance = load_csv("attendance.csv")
hiring = load_csv("hiring.csv")
productivity = load_csv("productivity.csv")
probation = load_csv("probation.csv")
manager_changes = load_csv("manager_changes.csv")
headcount_history = load_csv("headcount_history.csv")
critical_roles = load_csv("critical_roles.csv")

shared_df = st.session_state.get("shared_peoplepulse_dataset")

if shared_df is not None:
    # A single upload can serve as an employee dataset, but it must not
    # silently replace unrelated attendance, hiring, or planning event files.
    employees = shared_df.copy()


def metric(label, value):
    st.metric(label, value)

def chart_bar(df, x, y=None, title=None, color=None):
    if df.empty or x not in df.columns:
        st.info("No suitable records are available for this chart.")
        return
    if y and y in df.columns:
        fig = px.bar(df, x=x, y=y, color=color, title=title)
    else:
        fig = px.histogram(df, x=x, color=color, title=title)
    st.plotly_chart(fig, use_container_width=True)

st.sidebar.header("Analytics Modules")
page = st.sidebar.radio(
    "Navigate to",
    [
        "Executive Overview",
        "Attendance Analytics",
        "Hiring Analytics",
        "Productivity Analytics",
        "Workforce Planning",
        "Upload Dataset"
    ]
)
st.sidebar.divider()

st.sidebar.caption("Public demo: CSV-based; no database password required.")
st.sidebar.caption("Event data is labelled SIMULATED_DEMO where provided.")



# 1. EXECUTIVE OVERVIEW
# --------------------------------------------------
# 1. EXECUTIVE OVERVIEW
# --------------------------------------------------
if page == "Executive Overview":
    st.header("Executive Overview")

    # --------------------------------------------------
    # EMPLOYEE ATTRITION ANALYTICS
    # --------------------------------------------------
    st.caption(
        "Source: IBM HR employee dataset. "
        "These metrics describe the supplied dataset, not a live company workforce."
    )

    def normalise_columns(source_df):
        """Make CSV column names consistent for analysis."""
        result = source_df.copy()
        result.columns = [
            str(column).strip().lower().replace(" ", "_")
            for column in result.columns
        ]
        return result

    def get_column(source_df, *names):
        """Return the first matching column name."""
        for name in names:
            key = name.strip().lower().replace(" ", "_")
            if key in source_df.columns:
                return key
        return None

    # Use the employee CSV already loaded at the top of app_public.py.
    employee_df = normalise_columns(employees)

    attrition_col = get_column(
        employee_df, "Attrition", "EmployeeAttrition"
    )
    department_col = get_column(
        employee_df, "Department", "Function", "Team"
    )
    tenure_col = get_column(
        employee_df, "YearsAtCompany", "TenureYears"
    )
    overtime_col = get_column(
        employee_df, "OverTime", "Overtime"
    )
    satisfaction_col = get_column(
        employee_df, "JobSatisfaction", "Job Satisfaction"
    )

    if employee_df.empty:
        st.warning("The employee dataset is empty.")

    elif attrition_col is None:
        st.warning(
            "Attrition KPIs are unavailable because employees.csv "
            "does not contain an Attrition column."
        )
        st.metric("Employee Records", f"{len(employee_df):,}")

    else:
        attrition_values = (
            employee_df[attrition_col]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        left_mask = attrition_values.isin(
            ["yes", "1", "true", "left"]
        )
        stayed_mask = attrition_values.isin(
            ["no", "0", "false", "stayed"]
        )
        valid_mask = left_mask | stayed_mask

        total_records = len(employee_df)
        valid_count = int(valid_mask.sum())
        left_count = int(left_mask.sum())
        stayed_count = int(stayed_mask.sum())

        attrition_rate = (
            left_count / valid_count * 100
            if valid_count else 0
        )

        st.subheader("Workforce Summary")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Employee Records", f"{total_records:,}")
        c2.metric("Employees Stayed", f"{stayed_count:,}")
        c3.metric("Employees Left", f"{left_count:,}")
        c4.metric("Attrition Rate", f"{attrition_rate:.2f}%")

        if valid_count < total_records:
            st.info(
                f"{total_records - valid_count} record(s) have missing "
                "or unrecognised attrition values and are excluded "
                "from the attrition rate."
            )

        st.divider()
        

        # --------------------------------------------------
        # ATTRITION BY DEPARTMENT
        # --------------------------------------------------
        if department_col is not None:
            st.subheader("Attrition by Department")

            department_data = pd.DataFrame({
                "Department": (
                    employee_df[department_col]
                    .fillna("Unknown")
                    .astype(str)
                ),
                "Attrition_Left": left_mask,
                "Attrition_Valid": valid_mask
            })

            department_summary = (
                department_data.groupby("Department", dropna=False)
                .agg(
                    headcount=("Department", "size"),
                    employees_left=("Attrition_Left", "sum"),
                    valid_records=("Attrition_Valid", "sum")
                )
                .reset_index()
            )

            department_summary["attrition_rate_pct"] = (
                department_summary["employees_left"]
                / department_summary["valid_records"].replace(0, float("nan"))
                * 100
            ).round(2)

            fig = px.bar(
                department_summary,
                x="Department",
                y="attrition_rate_pct",
                text="attrition_rate_pct",
                hover_data=["headcount", "employees_left"],
                title="Attrition Rate by Department (%)"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Department-Level Talent Health Scorecard")
            st.dataframe(
                department_summary,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(
                "Department analysis requires a Department, Function "
                "or Team column."
            )

        # --------------------------------------------------
        # ATTRITION BY TENURE
        # --------------------------------------------------
        if tenure_col is not None:
            st.subheader("Attrition by Tenure")

            tenure_data = pd.DataFrame({
                "YearsAtCompany": pd.to_numeric(
                    employee_df[tenure_col], errors="coerce"
                ),
                "Attrition_Left": left_mask,
                "Attrition_Valid": valid_mask
            }).dropna(subset=["YearsAtCompany"])

            tenure_data["Tenure Group"] = pd.cut(
                tenure_data["YearsAtCompany"],
                bins=[-1, 1, 4, 9, float("inf")],
                labels=[
                    "0-1 years",
                    "2-4 years",
                    "5-9 years",
                    "10+ years"
                ]
            )

            tenure_summary = (
                tenure_data.groupby("Tenure Group", observed=False)
                .agg(
                    headcount=("Attrition_Valid", "size"),
                    employees_left=("Attrition_Left", "sum"),
                    valid_records=("Attrition_Valid", "sum")
                )
                .reset_index()
            )

            tenure_summary["attrition_rate_pct"] = (
                tenure_summary["employees_left"]
                / tenure_summary["valid_records"].replace(0, float("nan"))
                * 100
            ).round(2)

            fig = px.bar(
                tenure_summary,
                x="Tenure Group",
                y="attrition_rate_pct",
                text="attrition_rate_pct",
                hover_data=["headcount", "employees_left"],
                title="Attrition Rate by Tenure (%)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Tenure analysis requires YearsAtCompany or TenureYears."
            )

        # --------------------------------------------------
        # ATTRITION BY DEPARTMENT AND OVERTIME
        # --------------------------------------------------
        if department_col is not None and overtime_col is not None:
            st.subheader("Attrition by Department and Overtime")

            overtime_data = pd.DataFrame({
                "Department": (
                    employee_df[department_col]
                    .fillna("Unknown")
                    .astype(str)
                ),
                "OverTime": (
                    employee_df[overtime_col]
                    .fillna("Unknown")
                    .astype(str)
                ),
                "Attrition_Left": left_mask,
                "Attrition_Valid": valid_mask
            })

            overtime_summary = (
                overtime_data.groupby(
                    ["Department", "OverTime"], dropna=False
                )
                .agg(
                    headcount=("Attrition_Valid", "size"),
                    employees_left=("Attrition_Left", "sum"),
                    valid_records=("Attrition_Valid", "sum")
                )
                .reset_index()
            )

            overtime_summary["attrition_rate_pct"] = (
                overtime_summary["employees_left"]
                / overtime_summary["valid_records"].replace(0, float("nan"))
                * 100
            ).round(2)

            fig = px.bar(
                overtime_summary,
                x="OverTime",
                y="attrition_rate_pct",
                color="Department",
                barmode="group",
                hover_data=["headcount", "employees_left"],
                title="Attrition by Department and Overtime (%)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Department/overtime analysis requires Department and OverTime."
            )

        # --------------------------------------------------
        # RULE-BASED ATTRITION SCREENING
        # --------------------------------------------------
        st.divider()
        st.subheader("Attrition Risk Analytics")
        st.caption(
            "Rule-based screening of historical records, not a prediction "
            "of whether an individual employee will leave."
        )

        if (
            overtime_col is not None
            and tenure_col is not None
            and satisfaction_col is not None
        ):
            risk_data = employee_df.copy()

            risk_data["_overtime"] = (
                risk_data[overtime_col]
                .astype(str)
                .str.strip()
                .str.lower()
            )
            risk_data["_tenure"] = pd.to_numeric(
                risk_data[tenure_col], errors="coerce"
            )
            risk_data["_satisfaction"] = pd.to_numeric(
                risk_data[satisfaction_col], errors="coerce"
            )

            risk_data["Risk_Flag"] = (
                risk_data["_overtime"].isin(["yes", "true", "1"])
                & (risk_data["_tenure"] <= 2)
                & (risk_data["_satisfaction"] <= 2)
            )

            flagged = risk_data[risk_data["Risk_Flag"]]
            flagged_count = len(flagged)

            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Records Meeting All 3 Rules",
                f"{flagged_count:,}"
            )
            c2.metric(
                "Share of Dataset",
                f"{flagged_count / len(risk_data) * 100:.2f}%"
                if len(risk_data) else "0.00%"
            )

            if flagged_count and attrition_col is not None:
                flagged_values = (
                    flagged[attrition_col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )
                flagged_valid = flagged_values.isin(
                    ["yes", "1", "true", "left", "no", "0", "false", "stayed"]
                )
                flagged_left = flagged_values.isin(
                    ["yes", "1", "true", "left"]
                )

                historical_rate = (
                    flagged_left.sum() / flagged_valid.sum() * 100
                    if flagged_valid.sum() else None
                )
                c3.metric(
                    "Historical Attrition in This Group",
                    f"{historical_rate:.2f}%"
                    if historical_rate is not None else "N/A"
                )
            else:
                c3.metric("Historical Attrition in This Group", "N/A")

            st.caption(
                "Screening rule: overtime = Yes, tenure ≤ 2 years, "
                "and job satisfaction ≤ 2. This illustrative rule is "
                "not a validated early-warning system."
            )
        else:
            st.info(
                "Screening requires OverTime, YearsAtCompany and "
                "JobSatisfaction columns."
            )

    # --------------------------------------------------
    # MANAGER CHANGE ANALYTICS
    # --------------------------------------------------
    st.divider()
    st.subheader("Manager Change Analytics")
    if st.session_state.get("shared_peoplepulse_dataset") is not None:
        st.caption("Manager-change analysis uses the default manager_changes.csv file; the uploaded file is not treated as manager-change events.")
    else:
        st.caption("Source: SIMULATED_DEMO manager-change records. These demonstration records are not verified company events.")

    manager_df = normalise_columns(manager_changes)

    manager_employee_col = get_column(
        manager_df, "EmployeeID", "employee_id"
    )
    manager_date_col = get_column(
        manager_df, "EffectiveDate", "effective_date", "ChangeDate"
    )
    manager_source_col = get_column(
        manager_df, "DataSource", "data_source"
    )

    if manager_df.empty:
        st.info("No manager-change records are available.")
    elif manager_employee_col is None or manager_date_col is None:
        st.warning(
            "Manager-change CSV needs EmployeeID and EffectiveDate "
            "(or equivalent) columns."
        )
        st.write("Available columns:", list(manager_df.columns))
    else:
        manager_df[manager_date_col] = pd.to_datetime(
            manager_df[manager_date_col], errors="coerce"
        )

        if manager_source_col is not None:
            st.caption(
                "Data source labels: "
                + ", ".join(
                    manager_df[manager_source_col]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
            )

        c1, c2 = st.columns(2)
        c1.metric("Manager Change Records", f"{len(manager_df):,}")
        c2.metric(
            "Distinct Employees Recorded",
            f"{manager_df[manager_employee_col].nunique():,}"
        )

        valid_manager_dates = manager_df.dropna(
            subset=[manager_date_col]
        ).copy()

        if not valid_manager_dates.empty:
            valid_manager_dates["Change Month"] = (
                valid_manager_dates[manager_date_col]
                .dt.to_period("M")
                .astype(str)
            )

            monthly_changes = (
                valid_manager_dates.groupby("Change Month")
                .size()
                .reset_index(name="Change Records")
                .sort_values("Change Month")
            )

            fig = px.line(
                monthly_changes,
                x="Change Month",
                y="Change Records",
                markers=True,
                title="Manager Change Records by Month"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid manager-change dates are available.")

        st.dataframe(
            manager_df,
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------
    # PROBATION OUTCOME ANALYTICS
    # --------------------------------------------------
    st.divider()
    st.subheader("Probation Outcomes")
    if st.session_state.get("shared_peoplepulse_dataset") is not None:
        st.caption("Probation outcomes use the default probation.csv file; the uploaded file is not treated as probation events.")
    else:
        st.caption("Source: SIMULATED_DEMO probation records. These demonstration records are not verified company outcomes.")

    probation_df = normalise_columns(probation)

    probation_outcome_col = get_column(
        probation_df, "ProbationOutcome", "probation_outcome", "Outcome"
    )
    probation_employee_col = get_column(
        probation_df, "EmployeeID", "employee_id"
    )
    probation_start_col = get_column(
        probation_df, "ProbationStartDate", "probation_start_date"
    )
    probation_end_col = get_column(
        probation_df, "ProbationEndDate", "probation_end_date"
    )
    probation_exit_col = get_column(
        probation_df, "ExitDate", "exit_date"
    )

    if probation_df.empty:
        st.info("No probation records are available.")
    elif probation_outcome_col is None:
        st.warning(
            "The probation CSV does not contain a ProbationOutcome column."
        )
        st.write("Available columns:", list(probation_df.columns))
    else:
        for date_col in [
            probation_start_col,
            probation_end_col,
            probation_exit_col
        ]:
            if date_col is not None:
                probation_df[date_col] = pd.to_datetime(
                    probation_df[date_col], errors="coerce"
                )

        probation_df[probation_outcome_col] = (
            probation_df[probation_outcome_col]
            .astype("string")
            .str.strip()
            .str.title()
        )

        outcome_values = probation_df[probation_outcome_col]
        passed_count = int(outcome_values.eq("Passed").sum())
        extended_count = int(outcome_values.eq("Extended").sum())
        failed_count = int(outcome_values.eq("Failed").sum())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Probation Records", f"{len(probation_df):,}")
        c2.metric("Passed", f"{passed_count:,}")
        c3.metric("Extended", f"{extended_count:,}")
        c4.metric("Failed", f"{failed_count:,}")

        if probation_exit_col is not None:
            exit_count = int(probation_df[probation_exit_col].notna().sum())
            st.metric("Records with Exit Date", f"{exit_count:,}")

        outcome_summary = (
            outcome_values
            .fillna("Unknown")
            .replace("", "Unknown")
            .value_counts()
            .rename_axis("Probation Outcome")
            .reset_index(name="Records")
        )

        fig = px.bar(
            outcome_summary,
            x="Probation Outcome",
            y="Records",
            text="Records",
            title="Probation Outcome Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)

        if probation_exit_col is not None:
            st.markdown("#### Records with Exit Dates")
            exit_records = probation_df[
                probation_df[probation_exit_col].notna()
            ].copy()

            if exit_records.empty:
                st.info("No exit dates are recorded in the probation dataset.")
            else:
                display_columns = [
                    col for col in [
                        probation_employee_col,
                        probation_outcome_col,
                        probation_start_col,
                        probation_end_col,
                        probation_exit_col
                    ]
                    if col is not None
                ]
                st.dataframe(
                    exit_records[display_columns],
                    use_container_width=True,
                    hide_index=True
                )

        st.caption(
            "A recorded exit date does not prove that probation failure "
            "caused the exit."
        )

        with st.expander("View all probation records"):
            st.dataframe(
                probation_df,
                use_container_width=True,
                hide_index=True
            )
# 2. ATTENDANCE ANALYTICS

# --------------------------------------------------
# 2. ATTENDANCE ANALYTICS
# --------------------------------------------------


elif page == "Attendance Analytics":

    st.header("Attendance Analytics")
    st.caption("Attendance, absence and leave reporting")

    # --------------------------------------------------
    # LOAD SHARED UPLOAD OR DEFAULT DEMO DATA
    # --------------------------------------------------

    shared_df = st.session_state.get("shared_peoplepulse_dataset")

    if shared_df is not None:
        attendance = shared_df.copy()
        filename = st.session_state.get(
            "shared_peoplepulse_filename",
            "Uploaded dataset"
        )
        st.caption(f"Source: Uploaded dataset — {filename}")
    else:
        attendance = load_csv("attendance.csv")
        st.caption(
            "Source: attendance.csv — SIMULATED_DEMO records. "
            "These are demonstration records, not actual company attendance."
        )

    if attendance.empty:
        st.warning("The selected dataset contains no records.")
        st.stop()

    # --------------------------------------------------
    # RECOGNISE COLUMN NAMES
    # --------------------------------------------------

    def normalise_column_name(column):
        return (
            str(column).strip().lower()
            .replace("_", "")
            .replace(" ", "")
            .replace("-", "")
        )

    column_lookup = {
        normalise_column_name(col): col
        for col in attendance.columns
    }

    date_col = next(
        (
            column_lookup[name]
            for name in ["attendancedate", "date", "workdate"]
            if name in column_lookup
        ),
        None
    )

    status_col = next(
        (
            column_lookup[name]
            for name in ["status", "attendancestatus", "attendance"]
            if name in column_lookup
        ),
        None
    )

    employee_col = next(
        (
            column_lookup[name]
            for name in ["employeeid", "employeenumber", "employee"]
            if name in column_lookup
        ),
        None
    )

    department_col = next(
        (
            column_lookup[name]
            for name in ["department", "function", "team"]
            if name in column_lookup
        ),
        None
    )

    working_hours_col = column_lookup.get("workinghours")
    scheduled_hours_col = column_lookup.get("scheduledhours")
    leave_type_col = column_lookup.get("leavetype")

    # --------------------------------------------------
    # CHECK REQUIRED COLUMNS
    # --------------------------------------------------

    if status_col is None:
        st.warning(
            "Attendance analytics cannot be calculated from this dataset "
            "because an attendance status column is missing."
        )
        st.write("Columns found:", list(attendance.columns))
        st.info(
            "Required: a status column such as Status or AttendanceStatus. "
            "Optional: AttendanceDate, EmployeeID, Department and WorkingHours."
        )
        st.stop()

    # Standardise recognised column names.
    rename_columns = {status_col: "status"}

    if date_col is not None:
        rename_columns[date_col] = "attendance_date"

    if employee_col is not None:
        rename_columns[employee_col] = "employee_id"

    if department_col is not None:
        rename_columns[department_col] = "Department"

    if working_hours_col is not None:
        rename_columns[working_hours_col] = "working_hours"

    if scheduled_hours_col is not None:
        rename_columns[scheduled_hours_col] = "scheduled_hours"

    if leave_type_col is not None:
        rename_columns[leave_type_col] = "leave_type"

    attendance = attendance.rename(columns=rename_columns)

    # --------------------------------------------------
    # NORMALISE ATTENDANCE STATUS
    # --------------------------------------------------

    attendance["status"] = (
        attendance["status"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace("_", " ", regex=False)
        .str.replace("-", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
    )

    status_aliases = {
        "present": "present",
        "absent": "absent",
        "leave": "leave",
        "on leave": "leave",
        "sick leave": "leave",
        "casual leave": "leave",
        "work from home": "wfh",
        "wfh": "wfh",
        "remote": "wfh",
        "not scheduled": "not scheduled",
        "notscheduled": "not scheduled",
    }

    attendance["status"] = attendance["status"].replace(status_aliases)

    # --------------------------------------------------
    # CALCULATE METRICS FROM THE SELECTED DATASET
    # --------------------------------------------------

    present = int((attendance["status"] == "present").sum())
    absent = int((attendance["status"] == "absent").sum())
    leave = int((attendance["status"] == "leave").sum())
    wfh = int((attendance["status"] == "wfh").sum())

    not_scheduled = int(
        (attendance["status"] == "not scheduled").sum()
    )

    eligible = present + absent + leave + wfh

    absence_rate = (
        absent / eligible * 100
        if eligible > 0
        else 0
    )

    # --------------------------------------------------
    # ATTENDANCE KPI CARDS
    # --------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Attendance Records", f"{len(attendance):,}")
    c2.metric("Present", f"{present:,}")
    c3.metric("Absent", f"{absent:,}")
    c4.metric("Recorded Absence Rate", f"{absence_rate:.2f}%")

    st.caption(
        "Recorded absence rate = Absent / "
        "(Present + Absent + Leave + Work From Home). "
        "Not scheduled records are excluded. This is a record-based rate, "
        "not a full scheduled-workday absenteeism rate."
    )

    st.caption(
        f"Leave: {leave:,} | Not scheduled: {not_scheduled:,} | "
        f"Work from home: {wfh:,}"
    )

    # --------------------------------------------------
    # ATTENDANCE STATUS CHARTS
    # --------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Attendance Status")

        status_summary = (
            attendance["status"]
            .replace("", "Unknown")
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Records")
        )

        fig = px.bar(
            status_summary,
            x="Status",
            y="Records",
            text_auto=True,
            title="Records by Attendance Status"
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Attendance Outcomes")

        outcomes = pd.DataFrame({
            "Status": [
                "Present", "Absent", "Leave", "Work From Home"
            ],
            "Records": [present, absent, leave, wfh]
        })

        fig = px.bar(
            outcomes,
            x="Status",
            y="Records",
            text_auto=True,
            title="Present, Absent, Leave and WFH"
        )

        st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------
    # RECORDS BY DEPARTMENT
    # --------------------------------------------------

    if "Department" in attendance.columns:
        st.subheader("Records by Department")

        department_summary = (
            attendance.groupby("Department", dropna=False)
            .size()
            .reset_index(name="Records")
        )

        fig = px.bar(
            department_summary,
            x="Department",
            y="Records",
            text_auto=True,
            title="Attendance Records by Department"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(
            "Department-wise attendance is unavailable: "
            "the selected dataset has no Department, Function or Team column."
        )

    # --------------------------------------------------
    # ATTENDANCE TREND
    # --------------------------------------------------

    if "attendance_date" in attendance.columns:
        attendance["attendance_date"] = pd.to_datetime(
            attendance["attendance_date"],
            errors="coerce"
        )

        dated = attendance.dropna(subset=["attendance_date"])

        if not dated.empty:
            trend = (
                dated.groupby(dated["attendance_date"].dt.date)
                .size()
                .reset_index(name="Records")
            )

            trend.columns = ["Date", "Records"]

            st.subheader("Attendance Records Over Time")

            fig = px.line(
                trend,
                x="Date",
                y="Records",
                markers=True,
                title="Daily Attendance Record Trend"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid attendance dates are available.")
    else:
        st.info(
            "Attendance trends are unavailable: "
            "the selected dataset has no recognised date column."
        )

    # --------------------------------------------------
    # WORKING HOURS SUMMARY
    # --------------------------------------------------

    if "working_hours" in attendance.columns:
        attendance["working_hours"] = pd.to_numeric(
            attendance["working_hours"],
            errors="coerce"
        )

        st.subheader("Working Hours Summary")

        valid_hours = attendance["working_hours"].dropna()

        if not valid_hours.empty:
            h1, h2 = st.columns(2)

            h1.metric(
                "Average Working Hours",
                f"{valid_hours.mean():.2f}"
            )

            h2.metric(
                "Total Recorded Working Hours",
                f"{valid_hours.sum():,.2f}"
            )
        else:
            st.info("No valid working-hours values are available.")
    else:
        st.info(
            "Working-hours metrics are unavailable: "
            "the selected dataset has no WorkingHours column."
        )

    # --------------------------------------------------
    # ATTENDANCE DETAILS AND DOWNLOAD
    # --------------------------------------------------

    st.subheader("Attendance Details")

    st.dataframe(
        attendance,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download attendance records",
        data=attendance.to_csv(index=False).encode("utf-8"),
        file_name="peoplepulse_attendance.csv",
        mime="text/csv"
    )


# 3. HIRING ANALYTICS
elif page == "Hiring Analytics":
    st.header("Hiring Analytics")
    shared_hiring_df = st.session_state.get("shared_peoplepulse_dataset")
    if shared_hiring_df is not None:
        hiring = shared_hiring_df.copy()
    else:
        hiring = load_csv("hiring.csv")
    st.caption("Recruitment pipeline, hiring sources, hiring timelines and outcomes.")
    if st.session_state.get("shared_peoplepulse_dataset") is not None:
        st.caption("Source: uploaded dataset. Hiring metrics are shown only if recruitment status information is present.")
    else:
        st.caption("Source: hiring.csv — SIMULATED_DEMO data, not verified company recruitment records.")

    if hiring.empty:
        st.warning("Hiring data is unavailable. Check data/demo_package/hiring.csv.")
    else:
        hire = hiring.copy()

        # Normalise common date-column spelling variants, then parse dates.
        date_aliases = {
            "applicationdate": "ApplicationDate",
            "requisitionopendate": "RequisitionOpenDate",
            "offerdate": "OfferDate",
            "hiredate": "HireDate",
        }
        date_lookup = {
            str(col).strip().lower().replace("_", "").replace(" ", "").replace("-", ""): col
            for col in hire.columns
        }
        for normalized_name, canonical_name in date_aliases.items():
            original_name = date_lookup.get(normalized_name)
            if original_name is not None and original_name != canonical_name and canonical_name not in hire.columns:
                hire = hire.rename(columns={original_name: canonical_name})
        date_columns = ["ApplicationDate", "RequisitionOpenDate", "OfferDate", "HireDate"]
        for col in date_columns:
            if col in hire.columns:
                hire[col] = pd.to_datetime(hire[col], errors="coerce")

        
        # Stop if the uploaded file does not contain hiring data.
        required_columns = ["CandidateStatus"]

        # Accept common alternative column names.
        column_lookup = {
            str(col).strip().lower().replace("_", "").replace(" ", ""): col
            for col in hire.columns
        }

        status_column = next(
            (
                column_lookup[name]
                for name in ["candidatestatus", "status", "applicationstatus"]
                if name in column_lookup
            ),
            None,
        )

        if status_column is None:
            st.warning(
                "Hiring analytics cannot be calculated from this file because "
                "a CandidateStatus, Status, or ApplicationStatus column is missing."
            )
            st.write("Columns found in this file:", list(hire.columns))
            st.info(
                "Upload a recruitment dataset containing candidate statuses "
                "to view hiring KPIs. Your employee dataset has not been changed."
            )
            st.stop()

        hire["_Status"] = (
            hire[status_column].fillna("Unknown").astype(str).str.strip()
        )


        status_lower = hire["_Status"].str.strip().str.lower()

        # Match the original app.py KPI definitions: count by CandidateStatus only.
        hired_mask = status_lower.eq("hired")
        rejected_mask = status_lower.eq("rejected")
        pending_mask = status_lower.isin(
            ["pending", "in progress", "interview", "offered"]
        )

        total_records = len(hire)
        hired_count = int(hired_mask.sum())
        rejected_count = int(rejected_mask.sum())
        pending_count = int(pending_mask.sum())
        hiring_rate = hired_count / total_records * 100 if total_records else 0

        unique_candidates = (
            int(hire["CandidateID"].nunique())
            if "CandidateID" in hire.columns else total_records
        )
        unique_requisitions = (
            int(hire["JobRequisitionID"].nunique())
            if "JobRequisitionID" in hire.columns else 0
        )

        st.subheader("Recruitment Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Candidate Records", f"{total_records:,}")
        c2.metric("Hired", f"{hired_count:,}")
        c3.metric("Rejected", f"{rejected_count:,}")
        c4.metric("Hired / Candidate Records", f"{hiring_rate:.2f}%")

        st.caption(
            "Record-based hiring rate; it is not necessarily a unique-candidate conversion rate. "
            "Pending includes pending, in progress, interview and offered statuses."
        )
        if st.session_state.get("shared_peoplepulse_dataset") is None:
            st.caption("These records are SIMULATED_DEMO data, not verified company results.")

        with st.expander("Additional recruitment record counts"):
            a1, a2 = st.columns(2)
            a1.metric("Unique candidates", f"{unique_candidates:,}")
            a2.metric("Unique requisitions", f"{unique_requisitions:,}")
            st.metric("Pending / in-progress records", f"{pending_count:,}")

        st.divider()
        st.subheader("Recruitment Summary")

        status_summary = (
            hire["_Status"].value_counts(dropna=False)
            .rename_axis("Candidate Status")
            .reset_index(name="Records")
        )

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                status_summary,
                x="Candidate Status",
                y="Records",
                text="Records",
                title="Candidates by Hiring Status"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.pie(
                status_summary,
                names="Candidate Status",
                values="Records",
                title="Recruitment Pipeline Distribution",
                hole=0.35
            )
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(status_summary, use_container_width=True, hide_index=True)

        # Hiring source analysis
        st.subheader("Recruitment Source Analysis")

        if "HiringSource" in hire.columns:
            source_df = hire.copy()
            source_df["HiringSource"] = (
                source_df["HiringSource"].fillna("Not specified").astype(str)
            )
            source_df["_Hired"] = hired_mask.astype(int)

            source_summary = source_df.groupby("HiringSource", dropna=False).agg(
                Candidate_Records=("HiringSource", "size"),
                Hired_Records=("_Hired", "sum")
            ).reset_index()

            source_summary["Hired_Record_Rate_Pct"] = (
                source_summary["Hired_Records"]
                / source_summary["Candidate_Records"].replace(0, pd.NA) * 100
            ).round(2)

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(
                    source_summary.sort_values("Candidate_Records", ascending=False),
                    x="HiringSource",
                    y="Candidate_Records",
                    title="Candidate Records by Recruitment Source",
                    text="Candidate_Records"
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(
                    source_summary.sort_values(
                        "Hired_Record_Rate_Pct", ascending=False
                    ),
                    x="HiringSource",
                    y="Hired_Record_Rate_Pct",
                    title="Hired-Record Rate by Source (%)",
                    text="Hired_Record_Rate_Pct"
                )
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                source_summary.sort_values(
                    "Hired_Record_Rate_Pct", ascending=False
                ),
                use_container_width=True,
                hide_index=True
            )
            st.caption(
                "This rate is based on candidate records and is not necessarily a true "
                "recruitment conversion rate. Candidates may have different pipeline stages."
            )
        else:
            st.info("HiringSource is unavailable; source effectiveness cannot be analysed.")

        # Time-to-hire: application date to hire date
        st.subheader("Time-to-Hire Analysis")

        if {"ApplicationDate", "HireDate"}.issubset(hire.columns):
            time_to_hire = hire.loc[
                hire["ApplicationDate"].notna() & hire["HireDate"].notna()
            ].copy()
            time_to_hire["DaysToHire"] = (
                time_to_hire["HireDate"] - time_to_hire["ApplicationDate"]
            ).dt.days
            time_to_hire = time_to_hire.loc[time_to_hire["DaysToHire"] >= 0]

            if not time_to_hire.empty:
                avg_days = time_to_hire["DaysToHire"].mean()
                median_days = time_to_hire["DaysToHire"].median()

                c1, c2, c3 = st.columns(3)
                c1.metric("Average time-to-hire", f"{avg_days:.1f} days")
                c2.metric("Median time-to-hire", f"{median_days:.1f} days")
                c3.metric("Records with valid dates", f"{len(time_to_hire):,}")

                col1, col2 = st.columns(2)
                with col1:
                    fig = px.histogram(
                        time_to_hire,
                        x="DaysToHire",
                        nbins=20,
                        title="Distribution of Time-to-Hire (Days)"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    if "Department" in time_to_hire.columns:
                        dept_tth = time_to_hire.groupby("Department").agg(
                            Average_Days=("DaysToHire", "mean"),
                            Valid_Hires=("DaysToHire", "size")
                        ).reset_index()
                        dept_tth["Average_Days"] = dept_tth["Average_Days"].round(1)
                        fig = px.bar(
                            dept_tth.sort_values("Average_Days", ascending=False),
                            x="Department",
                            y="Average_Days",
                            title="Average Time-to-Hire by Department (Days)",
                            text="Average_Days"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Department is unavailable for time-to-hire comparisons.")
            else:
                st.info(
                    "No non-negative application-to-hire durations could be calculated "
                    "from the available dates."
                )
        else:
            st.info(
                "Time-to-hire requires both ApplicationDate and HireDate columns."
            )

        # Time-to-fill: requisition opening date to hire date
        st.subheader("Time-to-Fill Analysis")

        if {"RequisitionOpenDate", "HireDate"}.issubset(hire.columns):
            time_to_fill = hire.loc[
                hire["RequisitionOpenDate"].notna() & hire["HireDate"].notna()
            ].copy()
            time_to_fill["DaysToFill"] = (
                time_to_fill["HireDate"] - time_to_fill["RequisitionOpenDate"]
            ).dt.days
            time_to_fill = time_to_fill.loc[time_to_fill["DaysToFill"] >= 0]

            if not time_to_fill.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric(
                    "Average time-to-fill",
                    f"{time_to_fill['DaysToFill'].mean():.1f} days"
                )
                c2.metric(
                    "Median time-to-fill",
                    f"{time_to_fill['DaysToFill'].median():.1f} days"
                )
                c3.metric("Records with valid dates", f"{len(time_to_fill):,}")

                col1, col2 = st.columns(2)
                with col1:
                    fig = px.histogram(
                        time_to_fill,
                        x="DaysToFill",
                        nbins=20,
                        title="Distribution of Time-to-Fill (Days)"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    if "JobRole" in time_to_fill.columns:
                        role_fill = time_to_fill.groupby("JobRole").agg(
                            Average_Days=("DaysToFill", "mean"),
                            Records=("DaysToFill", "size")
                        ).reset_index()
                        role_fill["Average_Days"] = role_fill["Average_Days"].round(1)
                        fig = px.bar(
                            role_fill.sort_values("Average_Days", ascending=False),
                            x="JobRole",
                            y="Average_Days",
                            title="Average Time-to-Fill by Job Role (Days)"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("JobRole is unavailable for time-to-fill comparisons.")
            else:
                st.info("No valid requisition-open-to-hire durations were found.")
        else:
            st.info(
                "Time-to-fill requires RequisitionOpenDate and HireDate columns."
            )

        # Recruitment timeline
        st.subheader("Recruitment Timeline")

        if "ApplicationDate" in hire.columns and hire["ApplicationDate"].notna().any():
            timeline = hire.loc[hire["ApplicationDate"].notna()].copy()
            timeline["ApplicationMonth"] = (
                timeline["ApplicationDate"].dt.to_period("M").astype(str)
            )

            monthly_apps = timeline.groupby("ApplicationMonth").size().reset_index(
                name="Candidate Records"
            )
            fig = px.line(
                monthly_apps,
                x="ApplicationMonth",
                y="Candidate Records",
                markers=True,
                title="Candidate Records by Application Month"
            )
            st.plotly_chart(fig, use_container_width=True)

            if "HireDate" in timeline.columns:
                hired_timeline = timeline.loc[timeline["HireDate"].notna()].copy()
                if not hired_timeline.empty:
                    hired_timeline["HireMonth"] = (
                        hired_timeline["HireDate"].dt.to_period("M").astype(str)
                    )
                    monthly_hires = hired_timeline.groupby("HireMonth").size().reset_index(
                        name="Hired Records"
                    )
                    fig = px.bar(
                        monthly_hires,
                        x="HireMonth",
                        y="Hired Records",
                        title="Hired Records by Hire Month"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ApplicationDate is unavailable; recruitment timeline cannot be shown.")

        # Department and job-role outcomes
        st.subheader("Hiring Outcomes by Department")

        if "Department" in hire.columns:
            dept_hiring = hire.copy()
            dept_hiring["_Hired"] = hired_mask.astype(int)
            dept_summary = dept_hiring.groupby("Department", dropna=False).agg(
                Candidate_Records=("Department", "size"),
                Hired_Records=("_Hired", "sum")
            ).reset_index()

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(
                    dept_summary,
                    x="Department",
                    y="Candidate_Records",
                    title="Candidate Records by Department"
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(
                    dept_summary,
                    x="Department",
                    y="Hired_Records",
                    title="Hired Records by Department"
                )
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(dept_summary, use_container_width=True, hide_index=True)
        else:
            st.info("Department is unavailable in the selected recruitment dataset.")

        st.subheader("Hiring Outcomes by Job Role")

        if "JobRole" in hire.columns:
            role_hiring = hire.copy()
            role_hiring["_Hired"] = hired_mask.astype(int)
            role_summary = role_hiring.groupby("JobRole", dropna=False).agg(
                Candidate_Records=("JobRole", "size"),
                Hired_Records=("_Hired", "sum")
            ).reset_index()

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(
                    role_summary,
                    x="JobRole",
                    y="Candidate_Records",
                    title="Candidate Records by Job Role"
                )
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(
                    role_summary,
                    x="JobRole",
                    y="Hired_Records",
                    title="Hired Records by Job Role"
                )
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(role_summary, use_container_width=True, hide_index=True)
        else:
            st.info("JobRole is unavailable in the selected recruitment dataset.")

        # Detailed records
        st.subheader("Recruitment Records Explorer")
        st.caption("Showing up to 300 records from the selected recruitment dataset.")

        filter_col1, filter_col2 = st.columns(2)
        filtered_hire = hire.copy()

        with filter_col1:
            if "Department" in filtered_hire.columns:
                departments = sorted(
                    filtered_hire["Department"].dropna().astype(str).unique().tolist()
                )
                selected_depts = st.multiselect(
                    "Filter by department",
                    departments,
                    default=departments,
                    key="hiring_department_filter"
                )
                filtered_hire = filtered_hire[
                    filtered_hire["Department"].astype(str).isin(selected_depts)
                ]

        with filter_col2:
            statuses = sorted(filtered_hire["_Status"].dropna().astype(str).unique().tolist())
            selected_statuses = st.multiselect(
                "Filter by candidate status",
                statuses,
                default=statuses,
                key="hiring_status_filter"
            )
            filtered_hire = filtered_hire[
                filtered_hire["_Status"].astype(str).isin(selected_statuses)
            ]

        st.write(f"Filtered recruitment records: {len(filtered_hire):,}")
        st.dataframe(
            filtered_hire.drop(columns=["_Status"], errors="ignore").head(300),
            use_container_width=True,
            hide_index=True
        )
# 4. PRODUCTIVITY ANALYTICS
elif page == "Productivity Analytics":
    st.header("Productivity Analytics")
    st.caption("Performance ratings and task-completion reporting")

    # Use the active upload for this module, but only calculate metrics
    # when relevant productivity columns exist. Otherwise use the default demo file.
    shared_productivity_df = st.session_state.get("shared_peoplepulse_dataset")
    if shared_productivity_df is not None:
        productivity = shared_productivity_df.copy()
        st.caption("Source: uploaded dataset. Productivity metrics appear only when relevant performance or task columns are present.")
    else:
        productivity = load_csv("productivity.csv")
        st.caption("Source: productivity.csv — SIMULATED_DEMO records, not verified company performance results.")

    # Standardise column names and support common CSV column variants.
    productivity.columns = [
        str(col).strip().lower().replace(" ", "_")
        for col in productivity.columns
    ]

    aliases = {
        "productivityrecordid": "productivity_record_id",
        "employeeid": "employee_id",
        "reviewdate": "review_date",
        "reviewperiod": "review_period",
        "performancerating": "performance_rating",
        "goalcompletionrate": "goal_completion_rate",
        "tasksassigned": "tasks_assigned",
        "taskscompleted": "tasks_completed",
        "qualityscore": "quality_score",
        "jobrole": "job_role",
        "function": "department",
        "team": "department",
    }
    productivity = productivity.rename(
        columns={
            old: new for old, new in aliases.items()
            if old in productivity.columns and new not in productivity.columns
        }
    )

    # Attach department and job role from the employee CSV when available.
    if (
        "employee_id" in productivity.columns
        and not employees.empty
        and "EmployeeID" in employees.columns
    ):
        employee_columns = ["EmployeeID"]
        for col in ["Department", "JobRole"]:
            if col in employees.columns:
                employee_columns.append(col)

        employee_lookup = employees[employee_columns].copy()
        employee_lookup = employee_lookup.rename(
            columns={
                "EmployeeID": "employee_id",
                "Department": "department",
                "JobRole": "job_role",
            }
        )
        employee_lookup = employee_lookup.drop_duplicates("employee_id")

        for col in ["department", "job_role"]:
            if col not in productivity.columns and col in employee_lookup.columns:
                productivity = productivity.merge(
                    employee_lookup[["employee_id", col]],
                    on="employee_id",
                    how="left",
                )

    if productivity.empty:
        st.info("No productivity records are available in productivity.csv.")
        st.stop()

    # Task completion analytics.
    st.subheader("Task Completion Analytics")

    if {"tasks_completed", "tasks_assigned"}.issubset(productivity.columns):
        completed = pd.to_numeric(
            productivity["tasks_completed"], errors="coerce"
        )
        assigned = pd.to_numeric(
            productivity["tasks_assigned"], errors="coerce"
        )

        valid_tasks = (
            completed.notna()
            & assigned.notna()
            & (assigned > 0)
            & (completed >= 0)
            & (completed <= assigned)
        )

        total_completed = completed[valid_tasks].sum()
        total_assigned = assigned[valid_tasks].sum()
        completion_rate = (
            total_completed / total_assigned * 100
            if total_assigned > 0 else None
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Records with Valid Task Counts", f"{int(valid_tasks.sum()):,}")
        c2.metric("Tasks Completed", f"{total_completed:,.0f}")
        c3.metric(
            "Task Completion Rate",
            f"{completion_rate:.2f}%" if completion_rate is not None else "N/A",
        )

        st.caption(
            "Only records with valid task counts, positive assigned tasks, "
            "and completed tasks not exceeding assigned tasks are included."
        )

        if "department" in productivity.columns:
            task_data = productivity.loc[valid_tasks].copy()
            task_data["tasks_completed"] = completed[valid_tasks]
            task_data["tasks_assigned"] = assigned[valid_tasks]

            if not task_data.empty:
                department_tasks = (
                    task_data.groupby("department", dropna=False)
                    .agg(
                        Tasks_Completed=("tasks_completed", "sum"),
                        Tasks_Assigned=("tasks_assigned", "sum"),
                    )
                    .reset_index()
                )
                department_tasks["Completion_Rate"] = (
                    department_tasks["Tasks_Completed"]
                    / department_tasks["Tasks_Assigned"].replace(0, float("nan"))
                    * 100
                )

                st.subheader("Task Completion by Department")
                fig = px.bar(
                    department_tasks,
                    x="department",
                    y="Completion_Rate",
                    text_auto=".1f",
                    labels={
                        "department": "Department",
                        "Completion_Rate": "Completion Rate (%)",
                    },
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(
                    department_tasks, use_container_width=True, hide_index=True
                )
    else:
        st.info("Task-count columns are unavailable in this dataset.")

    # Performance rating analysis.
    st.divider()
    st.subheader("Employee Performance Rating Analysis")

    if "performance_rating" in productivity.columns:
        productivity["performance_rating"] = pd.to_numeric(
            productivity["performance_rating"], errors="coerce"
        )
        performance_df = productivity.dropna(
            subset=["performance_rating"]
        ).copy()

        if not performance_df.empty:
            c1, c2 = st.columns(2)
            c1.metric("Records with Ratings", f"{len(performance_df):,}")
            c2.metric(
                "Average Performance Rating",
                f"{performance_df['performance_rating'].mean():.2f}",
            )

            rating_counts = (
                performance_df["performance_rating"]
                .value_counts()
                .sort_index()
                .rename_axis("Performance Rating")
                .reset_index(name="Record Count")
            )

            st.subheader("Performance Rating Distribution")
            fig = px.bar(
                rating_counts,
                x="Performance Rating",
                y="Record Count",
                text="Record Count",
            )
            st.plotly_chart(fig, use_container_width=True)

            if "department" in performance_df.columns:
                department_performance = (
                    performance_df.groupby("department", dropna=False)
                    .agg(
                        Records=("performance_rating", "count"),
                        Average_Rating=("performance_rating", "mean"),
                    )
                    .reset_index()
                )
                department_performance["Average_Rating"] = (
                    department_performance["Average_Rating"].round(2)
                )

                st.subheader("Performance Ratings by Department")
                fig = px.bar(
                    department_performance,
                    x="department",
                    y="Average_Rating",
                    text="Average_Rating",
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(
                    department_performance,
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("No valid performance ratings are available.")
    else:
        st.info("This dataset has no performance-rating column.")

    # Goal completion and quality scores.
    if "goal_completion_rate" in productivity.columns:
        productivity["goal_completion_rate"] = pd.to_numeric(
            productivity["goal_completion_rate"], errors="coerce"
        )
        goal_values = productivity["goal_completion_rate"].dropna()

        if not goal_values.empty:
            st.subheader("Goal Completion")
            st.metric(
                "Average Goal Completion",
                f"{goal_values.mean():.1f}%",
            )

            if "department" in productivity.columns:
                goal_by_department = (
                    productivity.groupby("department", dropna=False)
                    ["goal_completion_rate"].mean()
                    .reset_index()
                )
                st.subheader("Goal Completion by Department")
                fig = px.bar(
                    goal_by_department,
                    x="department",
                    y="goal_completion_rate",
                    labels={"goal_completion_rate": "Average Goal Completion (%)"},
                )
                st.plotly_chart(fig, use_container_width=True)

    if "quality_score" in productivity.columns:
        productivity["quality_score"] = pd.to_numeric(
            productivity["quality_score"], errors="coerce"
        )
        quality_values = productivity["quality_score"].dropna()

        if not quality_values.empty:
            st.subheader("Quality Score")
            st.metric("Average Quality Score", f"{quality_values.mean():.2f}")

            if "department" in productivity.columns:
                quality_by_department = (
                    productivity.groupby("department", dropna=False)
                    ["quality_score"].mean()
                    .reset_index()
                )
                st.subheader("Quality Score by Department")
                fig = px.bar(
                    quality_by_department,
                    x="department",
                    y="quality_score",
                )
                st.plotly_chart(fig, use_container_width=True)

    # Performance rating trend by date.
    if (
        "review_date" in productivity.columns
        and "performance_rating" in productivity.columns
    ):
        productivity["review_date"] = pd.to_datetime(
            productivity["review_date"], errors="coerce"
        )
        dated = productivity.dropna(
            subset=["review_date", "performance_rating"]
        ).copy()

        if not dated.empty:
            trend = (
                dated.groupby(dated["review_date"].dt.date)["performance_rating"]
                .mean()
                .reset_index()
            )
            trend.columns = ["Review Date", "Average Rating"]

            st.subheader("Performance Rating Trend")
            fig = px.line(
                trend,
                x="Review Date",
                y="Average Rating",
                markers=True,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Performance ratings, task completion, goal completion, and quality are separate indicators. "
        "Demo records do not establish actual company performance."
    )

    st.subheader("Available Productivity Records")
    st.dataframe(productivity, use_container_width=True, hide_index=True)

    st.download_button(
        "Download productivity records",
        data=productivity.to_csv(index=False).encode("utf-8"),
        file_name="peoplepulse_productivity_demo.csv",
        mime="text/csv",
    )

# 5. WORKFORCE PLANNING
elif page == "Workforce Planning":
    st.header("Workforce Planning")
    st.caption("Workforce baseline, planning scenarios and role-level review")

    def wp_normalize(source):
        result = source.copy() if source is not None else pd.DataFrame()
        result.columns = [
            str(c).strip().lower().replace(" ", "_").replace("-", "_")
            for c in result.columns
        ]
        aliases = {
            "employeeid": "employee_id",
            "jobrole": "job_role",
            "yearsatcompany": "years_at_company",
            "probationstartdate": "probation_start_date",
            "probationenddate": "probation_end_date",
            "probationoutcome": "probation_outcome",
            "exitdate": "exit_date",
            "effectivedate": "effective_date",
            "snapshotdate": "snapshot_date",
            "iscriticalrole": "is_critical_role",
            "currentheadcount": "current_headcount",
            "openvacancies": "open_vacancies",
        }
        return result.rename(columns={
            old: new for old, new in aliases.items()
            if old in result.columns and new not in result.columns
        })

    planning_df = wp_normalize(employees)
    probation_df = wp_normalize(probation)
    manager_df = wp_normalize(manager_changes)
    history_df = wp_normalize(headcount_history)
    critical_df = wp_normalize(critical_roles)

    if st.session_state.get("shared_peoplepulse_dataset") is not None:
        st.caption("Employee baseline: uploaded dataset. Planning event files remain separate default CSV sources and are not inferred from the upload.")
    else:
        st.caption("Employee baseline: employees.csv. Event and planning files are demonstration data where marked SIMULATED_DEMO.")

    # Historical workforce baseline
    st.subheader("Workforce Baseline")
    total_employees = len(planning_df)
    st.metric("Employee Records in Dataset", f"{total_employees:,}")

    attrition_col = next(
        (c for c in ["attrition", "employee_attrition", "left_company"]
         if c in planning_df.columns), None
    )
    department_col = next(
        (c for c in ["department", "function", "team"]
         if c in planning_df.columns), None
    )
    role_col = next(
        (c for c in ["job_role", "role", "role_family"]
         if c in planning_df.columns), None
    )
    tenure_col = next(
        (c for c in ["years_at_company", "tenure_years", "tenure"]
         if c in planning_df.columns), None
    )

    if attrition_col:
        raw = planning_df[attrition_col].astype(str).str.strip().str.lower()
        planning_df["_left"] = raw.map({
            "yes": 1, "left": 1, "true": 1, "1": 1,
            "no": 0, "stayed": 0, "false": 0, "0": 0,
        })
    else:
        planning_df["_left"] = float("nan")

    baseline = planning_df.dropna(subset=["_left"]).copy()
    if department_col and not baseline.empty:
        summary = (
            baseline.groupby(department_col, dropna=False)
            .agg(
                Employee_Records=("_left", "size"),
                Employees_Left=("_left", "sum"),
                Historical_Attrition_Rate=("_left", "mean"),
            ).reset_index()
            .rename(columns={department_col: "Department"})
        )
        summary["Employees_Left"] = summary["Employees_Left"].astype(int)
        summary["Historical_Attrition_Rate"] = (
            summary["Historical_Attrition_Rate"] * 100
        ).round(2)
        st.dataframe(summary, use_container_width=True, hide_index=True)
        st.plotly_chart(
            px.bar(
                summary, x="Department", y="Historical_Attrition_Rate",
                title="Historical Attrition Rate by Department (%)",
                text="Historical_Attrition_Rate",
            ),
            use_container_width=True,
        )
    else:
        st.info("Department-level attrition requires department and attrition columns.")

    st.caption(
        "Employee record counts are dataset rows, not necessarily current headcount. "
        "Current headcount requires a verified, dated workforce snapshot."
    )

    # Probation outcomes and recorded exits
    st.divider()
    st.subheader("Probation Outcomes and Early Exits")
    if st.session_state.get("shared_peoplepulse_dataset") is not None:
        st.caption("Source: default probation.csv file; the uploaded employee dataset is not treated as probation events.")
    else:
        st.caption("Source: SIMULATED_DEMO probation records, not verified company HR data.")
    if not probation_df.empty and "probation_outcome" in probation_df.columns:
        probation_df["probation_outcome"] = (
            probation_df["probation_outcome"].astype(str).str.strip()
        )
        outcomes = probation_df["probation_outcome"].value_counts().reset_index()
        outcomes.columns = ["Probation Outcome", "Records"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Probation Records", f"{len(probation_df):,}")
        c2.metric("Passed", int(probation_df["probation_outcome"].str.lower().eq("passed").sum()))
        c3.metric("Failed", int(probation_df["probation_outcome"].str.lower().eq("failed").sum()))
        st.plotly_chart(
            px.bar(outcomes, x="Probation Outcome", y="Records",
                   title="Probation Outcome Distribution", text="Records"),
            use_container_width=True,
        )
        if "exit_date" in probation_df.columns:
            probation_df["exit_date"] = pd.to_datetime(
                probation_df["exit_date"], errors="coerce"
            )
            exits = probation_df[probation_df["exit_date"].notna()]
            st.metric("Records with Recorded Exit Dates", f"{len(exits):,}")
            if not exits.empty:
                cols = [c for c in [
                    "employee_id", "probation_outcome", "exit_date", "data_source"
                ] if c in exits.columns]
                st.dataframe(exits[cols], use_container_width=True, hide_index=True)
    else:
        st.info("Probation outcome data is unavailable in the loaded CSV.")

    # Manager changes compared with historical attrition
    st.divider()
    st.subheader("Manager Changes and Attrition Analysis")
    if st.session_state.get("shared_peoplepulse_dataset") is not None:
        st.caption("Manager-change source: default manager_changes.csv. This comparison is descriptive and does not establish that manager changes caused attrition.")
    else:
        st.caption("Manager-change records are SIMULATED_DEMO. This comparison is descriptive and does not establish that manager changes caused attrition.")
    if (
        not manager_df.empty
        and "employee_id" in manager_df.columns
        and "employee_id" in planning_df.columns
        and department_col
        and attrition_col
    ):
        changed_ids = manager_df["employee_id"].dropna().astype(str).unique()
        manager_view = planning_df.copy()
        manager_view["_employee_key"] = manager_view["employee_id"].astype(str)
        manager_view["_has_manager_change"] = manager_view["_employee_key"].isin(changed_ids)
        manager_view["_attrition_label"] = manager_view[attrition_col].astype(str)
        manager_view["_attrition_label"] = manager_view["_attrition_label"].str.strip()
        manager_summary = (
            manager_view.groupby([department_col, "_attrition_label"], dropna=False)
            .agg(
                Employee_Records=("_employee_key", "size"),
                Employees_With_Manager_Changes=("_has_manager_change", "sum"),
            ).reset_index()
        )
        manager_summary["Manager_Change_Coverage_%"] = (
            manager_summary["Employees_With_Manager_Changes"]
            / manager_summary["Employee_Records"].replace(0, float("nan")) * 100
        ).round(2)
        manager_summary = manager_summary.rename(columns={
            department_col: "Department",
            "_attrition_label": "Historical Attrition",
        })
        st.dataframe(manager_summary, use_container_width=True, hide_index=True)
        st.plotly_chart(
            px.bar(
                manager_summary, x="Department",
                y="Manager_Change_Coverage_%",
                color="Historical Attrition", barmode="group",
                title="Manager-Change Coverage by Department and Attrition",
            ),
            use_container_width=True,
        )
    else:
        st.info("Manager-change comparison needs matching employee IDs, department and attrition data.")

    # Illustrative headcount scenario
    st.divider()
    st.subheader("Illustrative Headcount Scenario")
    st.write("Change the assumptions to explore a hypothetical scenario. This is not a forecast.")
    c1, c2, c3 = st.columns(3)
    with c1:
        starting = st.number_input(
            "Assumed starting headcount", min_value=0,
            value=int(total_employees), step=1, key="wp_starting"
        )
    with c2:
        hires = st.number_input(
            "Assumed hires per quarter", min_value=0,
            value=0, step=1, key="wp_hires"
        )
    with c3:
        exits_per_quarter = st.number_input(
            "Assumed exits per quarter", min_value=0,
            value=0, step=1, key="wp_exits"
        )
    quarters = st.slider(
        "Planning horizon (quarters)", 1, 8, 4, key="wp_quarters"
    )
    scenario = []
    projected = starting
    scenario.append({"Period": "Starting", "Illustrative Headcount": projected})
    for q in range(1, quarters + 1):
        projected = max(0, projected + hires - exits_per_quarter)
        scenario.append({"Period": f"Q{q}", "Illustrative Headcount": projected})
    scenario_df = pd.DataFrame(scenario)
    st.plotly_chart(
        px.line(scenario_df, x="Period", y="Illustrative Headcount",
                markers=True, title="Illustrative Headcount Scenario"),
        use_container_width=True,
    )
    st.dataframe(scenario_df, use_container_width=True, hide_index=True)
    st.warning("Scenario values use only your entered assumptions; they are not a company forecast.")

    # Department-level talent health scorecard
    st.divider()
    st.subheader("Department-Level Talent Health Scorecard")
    if department_col and not baseline.empty:
        scorecard = (
            baseline.groupby(department_col, dropna=False)
            .agg(
                Employee_Records=("_left", "size"),
                Employees_Left=("_left", "sum"),
                Attrition_Rate=("_left", "mean"),
            ).reset_index()
            .rename(columns={department_col: "Department"})
        )
        scorecard["Employees_Left"] = scorecard["Employees_Left"].astype(int)
        scorecard["Attrition_Rate_%"] = (scorecard.pop("Attrition_Rate") * 100).round(2)
        st.dataframe(scorecard, use_container_width=True, hide_index=True)
        st.plotly_chart(
            px.bar(scorecard, x="Department", y="Attrition_Rate_%",
                   title="Department Talent Review — Historical Attrition",
                   text="Attrition_Rate_%"),
            use_container_width=True,
        )
        st.caption("This descriptive scorecard is not a verified company health rating.")
    else:
        st.info("Scorecard unavailable: department and usable attrition columns are required.")

    # Role-level attrition review
    st.divider()
    st.subheader("Role-Level Attrition Review")
    if role_col and not baseline.empty:
        role_summary = (
            baseline.groupby(role_col, dropna=False)
            .agg(
                Employee_Records=("_left", "size"),
                Employees_Left=("_left", "sum"),
                Historical_Attrition_Rate=("_left", "mean"),
            ).reset_index()
            .rename(columns={role_col: "Job Role"})
        )
        role_summary["Employees_Left"] = role_summary["Employees_Left"].astype(int)
        role_summary["Historical_Attrition_Rate"] = (
            role_summary["Historical_Attrition_Rate"] * 100
        ).round(2)
        role_summary = role_summary.sort_values("Historical_Attrition_Rate", ascending=False)
        st.dataframe(role_summary, use_container_width=True, hide_index=True)
        st.plotly_chart(
            px.bar(role_summary, x="Job Role", y="Historical_Attrition_Rate",
                   title="Historical Attrition by Job Role"),
            use_container_width=True,
        )
        st.caption("Historical attrition does not by itself identify a currently critical role.")
    else:
        st.info("Role review requires job role and attrition columns.")

    # Tenure breakdown
    st.divider()
    st.subheader("Employee Tenure Breakdown")
    if tenure_col:
        tenure_data = planning_df.copy()
        tenure_data[tenure_col] = pd.to_numeric(tenure_data[tenure_col], errors="coerce")
        tenure_data = tenure_data.dropna(subset=[tenure_col])
        if not tenure_data.empty:
            st.plotly_chart(
                px.histogram(tenure_data, x=tenure_col, nbins=10,
                             title="Employee Records by Years at Company"),
                use_container_width=True,
            )
        else:
            st.info("No numeric tenure values are available.")
    else:
        st.info("Tenure data is unavailable in the employee CSV.")

    # Headcount history
    st.divider()
    st.subheader("Headcount History")
    st.caption("Use as illustrative history only when the file is labelled SIMULATED_DEMO.")
    if not history_df.empty and {"snapshot_date", "headcount"}.issubset(history_df.columns):
        history_df["snapshot_date"] = pd.to_datetime(history_df["snapshot_date"], errors="coerce")
        history_df["headcount"] = pd.to_numeric(history_df["headcount"], errors="coerce")
        valid_history = history_df.dropna(subset=["snapshot_date", "headcount"])
        if not valid_history.empty:
            st.dataframe(history_df, use_container_width=True, hide_index=True)
            totals = valid_history.groupby("snapshot_date", as_index=False)["headcount"].sum()
            st.plotly_chart(
                px.line(totals, x="snapshot_date", y="headcount", markers=True,
                        title="Headcount by Snapshot Date"),
                use_container_width=True,
            )
        else:
            st.info("Headcount history contains no valid dated numeric values.")
    else:
        st.info("Headcount history CSV is unavailable or lacks required columns.")

    # Critical role review
    st.divider()
    st.subheader("Critical Role Review")
    st.caption("Critical-role and vacancy data may be SIMULATED_DEMO; verify with HR before use.")
    required = {"job_role", "is_critical_role"}
    if not critical_df.empty and required.issubset(critical_df.columns):
        if "open_vacancies" in critical_df.columns:
            critical_df["open_vacancies"] = pd.to_numeric(
                critical_df["open_vacancies"], errors="coerce"
            )
        if "current_headcount" in critical_df.columns:
            critical_df["current_headcount"] = pd.to_numeric(
                critical_df["current_headcount"], errors="coerce"
            )
        critical_text = critical_df["is_critical_role"].astype(str).str.strip().str.upper()
        pending = critical_text.isin(["REVIEW_REQUIRED", "", "NAN", "NONE", "NULL"])
        missing_vacancies = (
            int(critical_df["open_vacancies"].isna().sum())
            if "open_vacancies" in critical_df.columns else len(critical_df)
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Role Records", f"{len(critical_df):,}")
        c2.metric("Pending Criticality Review", f"{int(pending.sum()):,}")
        c3.metric("Missing Vacancy Counts", f"{missing_vacancies:,}")
        if pending.any() or missing_vacancies:
            st.warning("Some criticality classifications or vacancy counts need verification.")
        st.dataframe(critical_df, use_container_width=True, hide_index=True)
        if "open_vacancies" in critical_df.columns and critical_df["open_vacancies"].notna().any():
            vacancies = critical_df.dropna(subset=["open_vacancies"])
            st.plotly_chart(
                px.bar(vacancies, x="job_role", y="open_vacancies",
                       title="Open Vacancies by Job Role"),
                use_container_width=True,
            )
        else:
            st.info("No valid vacancy counts are available for a vacancy chart.")
    else:
        st.info("Critical-role CSV is unavailable or lacks role/classification columns.")




# --------------------------------------------------
# 6. UPLOAD DATASET - ONE SHARED FILE
# --------------------------------------------------

elif page == "Upload Dataset":

    st.header("Upload PeoplePulse Dataset")

    st.write(
        "Upload one CSV or Excel file as the active employee/shared dataset. "
        "Each analytics module will use it only where its columns fit that module; "
        "separate event datasets remain separate."
    )

    st.info(
        "Uploads are session-only. Original CSV files and MySQL tables "
        "are not overwritten. Analytics are calculated only when the "
        "uploaded data contains the required columns."
    )

    # --------------------------------------------------
    # SINGLE FILE UPLOAD
    # --------------------------------------------------

    uploaded_file = st.file_uploader(
        "Choose one CSV or Excel file",
        type=["csv", "xlsx"],
        key="peoplepulse_shared_file_uploader"
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                new_df = pd.read_csv(uploaded_file)
            else:
                new_df = pd.read_excel(uploaded_file)

            new_df.columns = (
                new_df.columns.astype(str).str.strip()
            )

            if new_df.empty:
                st.error("The uploaded file contains no records.")

            elif new_df.columns.duplicated().any():
                st.error(
                    "Duplicate column names found. "
                    "Please correct the file and upload it again."
                )

            else:
                st.session_state[
                    "shared_peoplepulse_dataset"
                ] = new_df.copy()

                st.session_state[
                    "shared_peoplepulse_filename"
                ] = uploaded_file.name

                st.success(
                    f"Dataset loaded successfully: "
                    f"{len(new_df):,} rows and "
                    f"{len(new_df.columns)} columns."
                )

        except Exception as error:
            st.error(f"Could not read the uploaded file: {error}")

    # --------------------------------------------------
    # ACTIVE DATASET
    # --------------------------------------------------

    shared_df = st.session_state.get(
        "shared_peoplepulse_dataset"
    )

    if shared_df is not None:

        filename = st.session_state.get(
            "shared_peoplepulse_filename",
            "Uploaded dataset"
        )

        st.subheader("Active shared dataset")

        st.write(f"**Filename:** {filename}")

        col1, col2 = st.columns(2)

        col1.metric("Total rows", f"{len(shared_df):,}")
        col2.metric("Total columns", f"{len(shared_df.columns):,}")

        st.subheader("Available columns")

        st.write(", ".join(map(str, shared_df.columns)))

        st.subheader("Data preview")

        st.dataframe(
            shared_df.head(20),
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download uploaded dataset as CSV",
            data=shared_df.to_csv(index=False).encode("utf-8"),
            file_name="peoplepulse_uploaded_dataset.csv",
            mime="text/csv"
        )

        if st.button(
            "Clear shared dataset",
            key="clear_shared_peoplepulse_dataset"
        ):
            st.session_state.pop(
                "shared_peoplepulse_dataset", None
            )
            st.session_state.pop(
                "shared_peoplepulse_filename", None
            )
            st.rerun()

    else:
        st.warning(
            "No shared upload is active. Your existing default CSV "
            "datasets remain available."
        )

# --------------------------------------------------
# DATA LIMITATIONS AND SOURCE
# --------------------------------------------------

st.divider()

with st.expander("Data sources and limitations"):
    st.markdown(
        """
        ### Data sources

        - **Employees:** IBM HR Attrition dataset.
        - **Attendance:** `attendance.csv` — SIMULATED_DEMO records.
        - **Hiring:** `hiring.csv` — SIMULATED_DEMO records.
        - **Productivity:** `productivity.csv` — SIMULATED_DEMO records.
        - **Workforce Planning:** Historical headcount and critical-role
          planning files, where available, may contain demo data.

        ### Important limitations

        - The active uploaded dataset is used as the employee/shared dataset.
        - Attendance can analyse the upload only when it has attendance-status data.
        - Hiring and productivity analytics require their own relevant columns; event files remain separate from an employee-only upload.
        - Missing files or empty datasets should not produce invented statistics.
        - Simulated records must be labelled SIMULATED_DEMO and must not
          be presented as actual company data.
        - This application uses descriptive analytics and user-defined
          planning scenarios. It does not use AI or machine learning.
        """
    )

st.sidebar.divider()
st.sidebar.caption("PeoplePulse | HR analytics demonstration project")
