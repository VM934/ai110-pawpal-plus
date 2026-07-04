from datetime import date, time

import streamlit as st

from pawpal_system import CareTask, Owner, PawPalScheduler, Pet


PRIORITIES = ["low", "medium", "high", "urgent"]
RECURRENCES = ["once", "daily", "weekdays", "weekends", "weekly"]
WEEKDAYS = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


st.set_page_config(page_title="PawPal+", page_icon="P", layout="wide")

st.title("PawPal+")

if "tasks" not in st.session_state:
    st.session_state.tasks = [
        {
            "title": "Breakfast feeding",
            "duration_minutes": 10,
            "priority": "urgent",
            "category": "feeding",
            "recurrence": "daily",
            "preferred_start": None,
            "fixed_start": "08:00",
            "days_of_week": (),
        },
        {
            "title": "Morning walk",
            "duration_minutes": 35,
            "priority": "high",
            "category": "exercise",
            "recurrence": "daily",
            "preferred_start": "08:30",
            "fixed_start": None,
            "days_of_week": (),
        },
        {
            "title": "Puzzle feeder enrichment",
            "duration_minutes": 20,
            "priority": "medium",
            "category": "enrichment",
            "recurrence": "weekends",
            "preferred_start": "10:00",
            "fixed_start": None,
            "days_of_week": (),
        },
    ]


def to_time_string(value):
    return value.strftime("%H:%M") if value else None


def from_time_string(value):
    if value is None:
        return None
    hour, minute = value.split(":", maxsplit=1)
    return time(int(hour), int(minute))


def build_task(row):
    return CareTask(
        title=row["title"],
        duration_minutes=int(row["duration_minutes"]),
        priority=row["priority"],
        category=row["category"],
        recurrence=row["recurrence"],
        preferred_start=from_time_string(row["preferred_start"]),
        fixed_start=from_time_string(row["fixed_start"]),
        days_of_week=tuple(row.get("days_of_week", ())),
    )


owner_col, pet_col = st.columns(2)
with owner_col:
    st.subheader("Owner")
    owner_name = st.text_input("Owner name", value="Jordan")
    availability_cols = st.columns(2)
    with availability_cols[0]:
        available_start = st.time_input("Available start", value=time(7, 30))
    with availability_cols[1]:
        available_end = st.time_input("Available end", value=time(18, 0))
    max_daily_minutes = st.number_input(
        "Daily care limit (minutes)",
        min_value=1,
        max_value=600,
        value=150,
    )

with pet_col:
    st.subheader("Pet")
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
    age_years = st.number_input("Age", min_value=0.0, max_value=40.0, value=3.0, step=0.5)
    plan_date = st.date_input("Plan date", value=date.today())

st.divider()

st.subheader("Tasks")
with st.form("task_form", clear_on_submit=False):
    task_cols = st.columns([2, 1, 1, 1])
    with task_cols[0]:
        title = st.text_input("Task", value="Brush coat")
    with task_cols[1]:
        duration = st.number_input("Minutes", min_value=1, max_value=240, value=15)
    with task_cols[2]:
        priority = st.selectbox("Priority", PRIORITIES, index=1)
    with task_cols[3]:
        category = st.text_input("Category", value="grooming")

    recurrence_cols = st.columns([1, 1, 1, 2])
    with recurrence_cols[0]:
        recurrence = st.selectbox("Recurrence", RECURRENCES)
    with recurrence_cols[1]:
        preferred = st.time_input("Preferred time", value=time(16, 30))
        use_preferred = st.checkbox("Use preferred", value=True)
    with recurrence_cols[2]:
        fixed = st.time_input("Fixed time", value=time(8, 0))
        use_fixed = st.checkbox("Use fixed", value=False)
    with recurrence_cols[3]:
        selected_days = st.multiselect("Weekly days", list(WEEKDAYS.keys()), default=["Saturday"])

    submitted = st.form_submit_button("Add task")
    if submitted:
        st.session_state.tasks.append(
            {
                "title": title,
                "duration_minutes": int(duration),
                "priority": priority,
                "category": category,
                "recurrence": recurrence,
                "preferred_start": to_time_string(preferred) if use_preferred else None,
                "fixed_start": to_time_string(fixed) if use_fixed else None,
                "days_of_week": tuple(WEEKDAYS[day] for day in selected_days)
                if recurrence == "weekly"
                else (),
            }
        )

if st.session_state.tasks:
    st.dataframe(st.session_state.tasks, use_container_width=True, hide_index=True)
else:
    st.info("No tasks added yet.")

button_cols = st.columns([1, 1, 5])
with button_cols[0]:
    generate = st.button("Generate plan", type="primary")
with button_cols[1]:
    if st.button("Clear tasks"):
        st.session_state.tasks = []
        st.rerun()

if generate:
    try:
        owner = Owner(
            owner_name,
            available_start=available_start,
            available_end=available_end,
            max_daily_minutes=int(max_daily_minutes),
        )
        pet = Pet(pet_name, species, age_years=age_years)
        tasks = [build_task(row) for row in st.session_state.tasks]
        plan = PawPalScheduler(owner, pet).generate_plan(tasks, plan_date=plan_date)
    except ValueError as error:
        st.error(str(error))
    else:
        metric_cols = st.columns(3)
        metric_cols[0].metric("Scheduled", len(plan.scheduled))
        metric_cols[1].metric("Skipped", len(plan.skipped))
        metric_cols[2].metric("Care minutes", plan.total_minutes)

        st.subheader("Daily Plan")
        st.dataframe(plan.as_rows(), use_container_width=True, hide_index=True)

        if plan.skipped:
            st.subheader("Skipped Tasks")
            st.dataframe(
                [
                    {
                        "task": item.task.title,
                        "priority": item.task.priority.name.lower(),
                        "reason": item.reason,
                    }
                    for item in plan.skipped
                ],
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("Plan Summary")
        st.code(plan.summary(), language="text")
