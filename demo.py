"""CLI walkthrough for the PawPal+ scheduling backend."""

from datetime import date

from pawpal_system import CareTask, Owner, PawPalScheduler, Pet, parse_time


def build_demo_plan():
    owner = Owner(
        name="Jordan",
        available_start=parse_time("07:30"),
        available_end=parse_time("18:00"),
        max_daily_minutes=150,
    )
    pet = Pet(name="Mochi", species="dog", age_years=3)
    tasks = [
        CareTask(
            "Breakfast feeding",
            10,
            priority="urgent",
            category="feeding",
            recurrence="daily",
            fixed_start=parse_time("08:00"),
        ),
        CareTask(
            "Heartworm medication",
            5,
            priority="urgent",
            category="medication",
            recurrence="weekly",
            days_of_week=(5,),
            preferred_start=parse_time("08:15"),
        ),
        CareTask(
            "Morning walk",
            35,
            priority="high",
            category="exercise",
            recurrence="daily",
            preferred_start=parse_time("08:30"),
        ),
        CareTask(
            "Puzzle feeder enrichment",
            20,
            priority="medium",
            category="enrichment",
            recurrence="weekends",
            preferred_start=parse_time("10:00"),
        ),
        CareTask(
            "Brush coat",
            15,
            priority="low",
            category="grooming",
            recurrence="weekly",
            days_of_week=(5,),
            preferred_start=parse_time("16:30"),
        ),
    ]
    scheduler = PawPalScheduler(owner, pet)
    return scheduler.generate_plan(tasks, plan_date=date(2026, 7, 4))


if __name__ == "__main__":
    print(build_demo_plan().summary())
