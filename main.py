from datetime import datetime, time

from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task


def at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(datetime.today(), time(hour, minute))


def main() -> None:
    owner = Owner(name="Jackson", available_time=90)

    rex = Pet(name="Rex", breed="Labrador")
    mia = Pet(name="Mia", breed="Siamese")
    owner.add_pet(rex)
    owner.add_pet(mia)

    rex.add_task(Task("Morning walk", at(7, 30), 30, Frequency.DAILY, Priority.HIGH))
    mia.add_task(Task("Breakfast", at(8, 0), 15, Frequency.DAILY, Priority.HIGH))
    rex.add_task(Task("Grooming", at(17, 0), 45, Frequency.WEEKLY, Priority.LOW))
    mia.add_task(Task("Play session", at(18, 30), 20, Frequency.ONCE, Priority.MEDIUM))

    scheduler = Scheduler(owner)
    scheduler.generate_schedule(day=datetime.today().date())

    print(f"Today's Schedule for {owner.name} ({owner.available_time} min available)")
    print("=" * 50)
    print(scheduler.display_plan())
    print()
    print("Reasoning")
    print("-" * 50)
    print(scheduler.explain_reasoning())


if __name__ == "__main__":
    main()
