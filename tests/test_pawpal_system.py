from datetime import date, time

import pytest

from pawpal_system import CareTask, Owner, PawPalScheduler, Pet, Priority, parse_time


def make_scheduler(owner=None):
    owner = owner or Owner("Jordan", parse_time("08:00"), parse_time("12:00"))
    pet = Pet("Mochi", "dog")
    return PawPalScheduler(owner, pet)


def titles(plan):
    return [item.task.title for item in plan.scheduled]


def skipped_titles(plan):
    return [item.task.title for item in plan.skipped]


def test_priority_controls_what_fits_under_daily_time_limit():
    scheduler = make_scheduler(
        Owner("Jordan", parse_time("08:00"), parse_time("12:00"), max_daily_minutes=30)
    )
    tasks = [
        CareTask("Brush coat", 20, priority="low"),
        CareTask("Medication", 30, priority="urgent"),
    ]

    plan = scheduler.generate_plan(tasks, plan_date=date(2026, 7, 4))

    assert titles(plan) == ["Medication"]
    assert skipped_titles(plan) == ["Brush coat"]
    assert "time limit" in plan.skipped[0].reason


def test_fixed_task_conflict_is_detected_and_skipped():
    scheduler = make_scheduler()
    tasks = [
        CareTask("Breakfast", 30, priority="urgent", fixed_start=parse_time("08:30")),
        CareTask("Medication", 20, priority="urgent", fixed_start=parse_time("08:45")),
    ]

    conflicts = scheduler.detect_conflicts(tasks)
    plan = scheduler.generate_plan(tasks, plan_date=date(2026, 7, 4))

    assert conflicts == [(tasks[0], tasks[1])]
    assert titles(plan) == ["Breakfast"]
    assert skipped_titles(plan) == ["Medication"]
    assert "conflicts" in plan.skipped[0].reason


def test_flexible_task_moves_after_occupied_preferred_slot():
    scheduler = make_scheduler()
    tasks = [
        CareTask("Vet call", 60, priority="high", fixed_start=parse_time("09:00")),
        CareTask("Walk", 30, priority="high", preferred_start=parse_time("09:15")),
    ]

    plan = scheduler.generate_plan(tasks, plan_date=date(2026, 7, 4))
    walk = next(item for item in plan.scheduled if item.task.title == "Walk")

    assert walk.start == time(10, 0)
    assert walk.end == time(10, 30)
    assert "preferred time" in walk.reason


def test_task_can_fit_exactly_at_owner_availability_boundary():
    scheduler = make_scheduler(Owner("Jordan", parse_time("08:00"), parse_time("09:00")))

    plan = scheduler.generate_plan(
        [CareTask("Long walk", 60, priority=Priority.HIGH)],
        plan_date=date(2026, 7, 4),
    )

    assert titles(plan) == ["Long walk"]
    assert plan.scheduled[0].start == time(8, 0)
    assert plan.scheduled[0].end == time(9, 0)


def test_task_that_exceeds_availability_window_is_skipped():
    scheduler = make_scheduler(Owner("Jordan", parse_time("08:00"), parse_time("09:00")))

    plan = scheduler.generate_plan(
        [CareTask("Too long", 61, priority="high")],
        plan_date=date(2026, 7, 4),
    )

    assert titles(plan) == []
    assert skipped_titles(plan) == ["Too long"]
    assert "No open time slot" in plan.skipped[0].reason


def test_recurring_tasks_only_appear_on_matching_dates():
    scheduler = make_scheduler()
    saturday = date(2026, 7, 4)
    tasks = [
        CareTask("Daily feeding", 10, recurrence="daily"),
        CareTask("Weekday daycare", 30, recurrence="weekdays"),
        CareTask("Weekend hike", 45, recurrence="weekends"),
        CareTask("Saturday meds", 5, recurrence="weekly", days_of_week=(5,)),
    ]

    plan = scheduler.generate_plan(tasks, plan_date=saturday)

    assert set(titles(plan)) == {"Daily feeding", "Saturday meds", "Weekend hike"}
    assert skipped_titles(plan) == ["Weekday daycare"]


def test_generate_plan_accepts_generator_inputs():
    scheduler = make_scheduler()
    task_source = (
        CareTask(f"Task {number}", 10, priority="medium") for number in range(2)
    )

    plan = scheduler.generate_plan(task_source, plan_date=date(2026, 7, 4))

    assert titles(plan) == ["Task 0", "Task 1"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"title": "", "duration_minutes": 10}, "task title"),
        ({"title": "Walk", "duration_minutes": 0}, "duration_minutes"),
        ({"title": "Walk", "duration_minutes": 10, "recurrence": "hourly"}, "recurrence"),
    ],
)
def test_task_validation_rejects_bad_inputs(kwargs, message):
    with pytest.raises(ValueError, match=message):
        CareTask(**kwargs)


def test_owner_validation_rejects_invalid_availability():
    with pytest.raises(ValueError, match="available_start"):
        Owner("Jordan", parse_time("18:00"), parse_time("08:00"))
