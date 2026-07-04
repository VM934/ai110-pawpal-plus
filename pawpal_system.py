"""Core PawPal+ domain models and scheduling logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import IntEnum
from typing import Iterable


class Priority(IntEnum):
    """Priority values sorted from least to most important."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

    @classmethod
    def from_value(cls, value: "Priority | str | int") -> "Priority":
        if isinstance(value, Priority):
            return value
        if isinstance(value, int):
            return Priority(value)
        normalized = value.strip().upper()
        return Priority[normalized]


@dataclass(frozen=True)
class Owner:
    """A pet owner with a daily availability window."""

    name: str
    available_start: time = time(7, 0)
    available_end: time = time(21, 0)
    max_daily_minutes: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("owner name is required")
        if minutes_since_midnight(self.available_start) >= minutes_since_midnight(
            self.available_end
        ):
            raise ValueError("available_start must be before available_end")
        if self.max_daily_minutes is not None and self.max_daily_minutes <= 0:
            raise ValueError("max_daily_minutes must be positive")


@dataclass(frozen=True)
class Pet:
    """A pet receiving care."""

    name: str
    species: str
    age_years: float | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("pet name is required")
        if not self.species.strip():
            raise ValueError("species is required")
        if self.age_years is not None and self.age_years < 0:
            raise ValueError("age_years cannot be negative")


@dataclass(frozen=True)
class CareTask:
    """One care activity that may be placed into the daily plan."""

    title: str
    duration_minutes: int
    priority: Priority | str | int = Priority.MEDIUM
    category: str = "general"
    recurrence: str = "once"
    preferred_start: time | None = None
    fixed_start: time | None = None
    days_of_week: tuple[int, ...] = field(default_factory=tuple)
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("task title is required")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        object.__setattr__(self, "priority", Priority.from_value(self.priority))
        object.__setattr__(self, "recurrence", self.recurrence.lower().strip())
        if self.recurrence not in {"once", "daily", "weekdays", "weekends", "weekly"}:
            raise ValueError("unsupported recurrence")
        if any(day < 0 or day > 6 for day in self.days_of_week):
            raise ValueError("days_of_week values must be 0 through 6")

    def occurs_on(self, plan_date: date) -> bool:
        """Return whether the task is due on the requested date."""

        weekday = plan_date.weekday()
        if self.recurrence in {"once", "daily"}:
            return True
        if self.recurrence == "weekdays":
            return weekday < 5
        if self.recurrence == "weekends":
            return weekday >= 5
        return not self.days_of_week or weekday in self.days_of_week


@dataclass(frozen=True)
class ScheduledTask:
    """A care task with an assigned start and end time."""

    task: CareTask
    start: time
    end: time
    reason: str

    @property
    def priority(self) -> Priority:
        return self.task.priority


@dataclass(frozen=True)
class SkippedTask:
    """A care task that could not be scheduled, plus the reason."""

    task: CareTask
    reason: str


@dataclass(frozen=True)
class DailyPlan:
    """The final daily schedule for one owner and pet."""

    owner: Owner
    pet: Pet
    plan_date: date
    scheduled: tuple[ScheduledTask, ...]
    skipped: tuple[SkippedTask, ...]

    @property
    def total_minutes(self) -> int:
        return sum(item.task.duration_minutes for item in self.scheduled)

    def as_rows(self) -> list[dict[str, str | int]]:
        return [
            {
                "start": format_time(item.start),
                "end": format_time(item.end),
                "task": item.task.title,
                "priority": item.task.priority.name.lower(),
                "duration": item.task.duration_minutes,
                "reason": item.reason,
            }
            for item in self.scheduled
        ]

    def summary(self) -> str:
        lines = [
            f"Daily plan for {self.pet.name} ({self.pet.species}) on {self.plan_date}:",
        ]
        if not self.scheduled:
            lines.append("  No tasks could be scheduled.")
        for item in self.scheduled:
            lines.append(
                "  "
                f"{format_time(item.start)}-{format_time(item.end)}: "
                f"{item.task.title} ({item.task.duration_minutes} min, "
                f"{item.task.priority.name.lower()}) - {item.reason}"
            )
        if self.skipped:
            lines.append("Skipped tasks:")
            for skipped in self.skipped:
                lines.append(f"  {skipped.task.title}: {skipped.reason}")
        lines.append(f"Total scheduled care time: {self.total_minutes} minutes")
        return "\n".join(lines)


class PawPalScheduler:
    """Greedy scheduler for one owner, one pet, and one day."""

    def __init__(self, owner: Owner, pet: Pet) -> None:
        self.owner = owner
        self.pet = pet

    def generate_plan(
        self,
        tasks: Iterable[CareTask],
        plan_date: date | None = None,
        max_minutes: int | None = None,
    ) -> DailyPlan:
        target_date = plan_date or date.today()
        minute_limit = max_minutes or self.owner.max_daily_minutes
        scheduled: list[ScheduledTask] = []
        skipped: list[SkippedTask] = []
        total_minutes = 0
        task_list = list(tasks)
        due_tasks = [task for task in task_list if task.occurs_on(target_date)]
        skipped.extend(
            SkippedTask(task, "Not due on this date.")
            for task in task_list
            if not task.occurs_on(target_date)
        )

        for task in sorted(
            [task for task in due_tasks if task.fixed_start is not None],
            key=lambda task: minutes_since_midnight(task.fixed_start or time(0, 0)),
        ):
            result = self._schedule_fixed(task, scheduled)
            if isinstance(result, ScheduledTask):
                scheduled.append(result)
                total_minutes += task.duration_minutes
            else:
                skipped.append(result)

        flexible_tasks = [task for task in due_tasks if task.fixed_start is None]
        flexible_tasks.sort(key=self._task_sort_key)

        for task in flexible_tasks:
            if minute_limit is not None and total_minutes + task.duration_minutes > minute_limit:
                skipped.append(
                    SkippedTask(task, "Skipped because the daily time limit would be exceeded.")
                )
                continue
            result = self._schedule_flexible(task, scheduled)
            if isinstance(result, ScheduledTask):
                scheduled.append(result)
                total_minutes += task.duration_minutes
            else:
                skipped.append(result)

        scheduled.sort(key=lambda item: minutes_since_midnight(item.start))
        return DailyPlan(
            owner=self.owner,
            pet=self.pet,
            plan_date=target_date,
            scheduled=tuple(scheduled),
            skipped=tuple(skipped),
        )

    def detect_conflicts(self, tasks: Iterable[CareTask]) -> list[tuple[CareTask, CareTask]]:
        fixed_tasks = [task for task in tasks if task.fixed_start is not None]
        conflicts: list[tuple[CareTask, CareTask]] = []
        for index, left in enumerate(fixed_tasks):
            left_start = minutes_since_midnight(left.fixed_start or time(0, 0))
            left_end = left_start + left.duration_minutes
            for right in fixed_tasks[index + 1 :]:
                right_start = minutes_since_midnight(right.fixed_start or time(0, 0))
                right_end = right_start + right.duration_minutes
                if intervals_overlap(left_start, left_end, right_start, right_end):
                    conflicts.append((left, right))
        return conflicts

    def _task_sort_key(self, task: CareTask) -> tuple[int, int, int, str]:
        preferred = (
            minutes_since_midnight(task.preferred_start)
            if task.preferred_start is not None
            else minutes_since_midnight(self.owner.available_start)
        )
        return (-int(task.priority), preferred, task.duration_minutes, task.title.lower())

    def _schedule_fixed(
        self, task: CareTask, scheduled: list[ScheduledTask]
    ) -> ScheduledTask | SkippedTask:
        assert task.fixed_start is not None
        start = minutes_since_midnight(task.fixed_start)
        end = start + task.duration_minutes
        window_start = minutes_since_midnight(self.owner.available_start)
        window_end = minutes_since_midnight(self.owner.available_end)

        if start < window_start or end > window_end:
            return SkippedTask(task, "Fixed time falls outside the owner's availability window.")
        if self._has_overlap(start, end, scheduled):
            return SkippedTask(task, "Fixed time conflicts with another scheduled task.")
        return ScheduledTask(
            task=task,
            start=task.fixed_start,
            end=time_from_minutes(end),
            reason="Placed at its fixed required time.",
        )

    def _schedule_flexible(
        self, task: CareTask, scheduled: list[ScheduledTask]
    ) -> ScheduledTask | SkippedTask:
        preferred = task.preferred_start or self.owner.available_start
        start = self._first_available_start(task, scheduled, preferred)
        used_preferred_fallback = False
        if start is None and task.preferred_start is not None:
            start = self._first_available_start(task, scheduled, self.owner.available_start)
            used_preferred_fallback = start is not None

        if start is None:
            return SkippedTask(task, "No open time slot fit inside the availability window.")

        end = start + task.duration_minutes
        reason = f"Scheduled by priority ({task.priority.name.lower()})"
        if task.preferred_start is not None and not used_preferred_fallback:
            reason += " near the preferred time."
        elif used_preferred_fallback:
            reason += " in the earliest fallback slot because the preferred time was full."
        else:
            reason += " in the earliest available slot."
        return ScheduledTask(task, time_from_minutes(start), time_from_minutes(end), reason)

    def _first_available_start(
        self, task: CareTask, scheduled: list[ScheduledTask], earliest: time
    ) -> int | None:
        candidate = max(
            minutes_since_midnight(self.owner.available_start),
            minutes_since_midnight(earliest),
        )
        day_end = minutes_since_midnight(self.owner.available_end)
        for start, end in self._open_windows(scheduled):
            candidate = max(candidate, start)
            if candidate + task.duration_minutes <= end and candidate + task.duration_minutes <= day_end:
                return candidate
        return None

    def _open_windows(self, scheduled: list[ScheduledTask]) -> list[tuple[int, int]]:
        window_start = minutes_since_midnight(self.owner.available_start)
        window_end = minutes_since_midnight(self.owner.available_end)
        windows: list[tuple[int, int]] = []
        cursor = window_start
        for item in sorted(scheduled, key=lambda entry: minutes_since_midnight(entry.start)):
            start = minutes_since_midnight(item.start)
            if cursor < start:
                windows.append((cursor, start))
            cursor = max(cursor, minutes_since_midnight(item.end))
        if cursor < window_end:
            windows.append((cursor, window_end))
        return windows

    def _has_overlap(
        self, start: int, end: int, scheduled: Iterable[ScheduledTask]
    ) -> bool:
        return any(
            intervals_overlap(
                start,
                end,
                minutes_since_midnight(item.start),
                minutes_since_midnight(item.end),
            )
            for item in scheduled
        )


def minutes_since_midnight(value: time) -> int:
    return value.hour * 60 + value.minute


def time_from_minutes(minutes: int) -> time:
    if minutes < 0 or minutes >= 24 * 60:
        raise ValueError("minutes must be within a single day")
    return time(minutes // 60, minutes % 60)


def parse_time(value: str) -> time:
    hour, minute = value.split(":", maxsplit=1)
    return time(int(hour), int(minute))


def format_time(value: time) -> str:
    return value.strftime("%H:%M")


def intervals_overlap(
    start_a: int,
    end_a: int,
    start_b: int,
    end_b: int,
) -> bool:
    return start_a < end_b and start_b < end_a
