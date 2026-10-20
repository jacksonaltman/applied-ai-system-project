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

    # Added deliberately out of chronological order
    mia.add_task(Task("Play session", at(18, 30), 20, Frequency.ONCE, Priority.MEDIUM))
    rex.add_task(Task("Grooming", at(17, 0), 45, Frequency.WEEKLY, Priority.LOW))
    mia.add_task(Task("Breakfast", at(8, 0), 15, Frequency.DAILY, Priority.HIGH))
    rex.add_task(Task("Morning walk", at(7, 30), 30, Frequency.DAILY, Priority.HIGH))
    # Deliberate conflicts: same time for different pets, and same pet overlapping
    rex.add_task(Task("Vet call", at(7, 30), 20, Frequency.ONCE, Priority.MEDIUM))
    rex.add_task(Task("Training", at(18, 40), 20, Frequency.ONCE, Priority.LOW))

    scheduler = Scheduler(owner)
    scheduler.complete_task(mia.tasks[1])  # mark Breakfast done (re-queues tomorrow's)

    def show(title, tasks):
        print(f"\n{title}")
        print("-" * 50)
        for t in tasks:
            mark = "x" if t.completed else " "
            print(f"[{mark}] {t.time:%a %H:%M}  {t.description} ({t.pet_name})")

    show("As added (unsorted)", scheduler.get_all_tasks())
    show("Sorted by time", scheduler.sort_by_time())
    show("Rex's tasks", scheduler.filter_tasks(pet_name="Rex"))
    show("Completed tasks", scheduler.filter_tasks(completed=True))
    show("Pending tasks for Mia", scheduler.filter_tasks(pet_name="Mia", completed=False))
    print()

    print("Conflict check (all pending tasks)")
    print("-" * 50)
    for w in scheduler.conflict_warnings() or ["No conflicts."]:
        print(w)
    print()

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
