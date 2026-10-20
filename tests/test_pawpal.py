from datetime import date, datetime, timedelta

import pytest

from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task

# Far-future dates keep Scheduler.complete_task (which uses the real "today")
# deterministic: the task's own date is always the later one.
DAY = datetime(2099, 1, 1)


def at(hour, minute=0, day=DAY):
    return day.replace(hour=hour, minute=minute)


def make_scheduler(available_time=480):
    owner = Owner("Sam", available_time)
    rex, mia = Pet("Rex", "Lab"), Pet("Mia", "Tabby")
    owner.add_pet(rex)
    owner.add_pet(mia)
    return Scheduler(owner), rex, mia


# --- basics ---

def test_mark_complete_changes_status():
    task = Task("Walk", at(8))
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet("Rex", "Lab")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Walk", at(8)))

    assert len(pet.tasks) == 1


def test_invalid_duration_rejected():
    with pytest.raises(ValueError):
        Task("Walk", at(8), duration=0)


# --- sorting ---

def test_sort_by_time_is_chronological_across_pets():
    sched, rex, mia = make_scheduler()
    rex.add_task(Task("Evening walk", at(18)))
    mia.add_task(Task("Breakfast", at(7)))
    rex.add_task(Task("Lunch", at(12)))

    result = sched.sort_by_time()

    assert [t.description for t in result] == ["Breakfast", "Lunch", "Evening walk"]


def test_sort_by_time_breaks_ties_by_priority():
    sched, rex, _ = make_scheduler()
    rex.add_task(Task("Low", at(9), priority=Priority.LOW))
    rex.add_task(Task("High", at(9), priority=Priority.HIGH))

    assert [t.description for t in sched.sort_by_time()] == ["High", "Low"]


def test_sort_by_time_handles_dates_not_just_clock_time():
    sched, rex, _ = make_scheduler()
    rex.add_task(Task("Tomorrow 8am", at(8, day=DAY + timedelta(days=1))))
    rex.add_task(Task("Today 9pm", at(21)))

    assert [t.description for t in sched.sort_by_time()] == ["Today 9pm", "Tomorrow 8am"]


def test_sort_with_no_tasks_returns_empty_list():
    sched, _, _ = make_scheduler()
    assert sched.sort_by_time() == []


# --- recurrence ---

def test_daily_task_creates_next_day_task():
    task = Task("Feed", at(8), frequency=Frequency.DAILY)

    nxt = task.mark_complete(today=DAY.date())

    assert task.completed is True
    assert nxt is not None
    assert nxt.time == at(8, day=DAY + timedelta(days=1))
    assert nxt.completed is False
    assert nxt.description == "Feed"
    assert nxt.frequency == Frequency.DAILY


def test_weekly_task_creates_task_one_week_later():
    task = Task("Bath", at(10), frequency=Frequency.WEEKLY)

    nxt = task.mark_complete(today=DAY.date())

    assert nxt.time == at(10, day=DAY + timedelta(weeks=1))


def test_one_off_task_does_not_recur():
    task = Task("Vet visit", at(10), frequency=Frequency.ONCE)
    assert task.mark_complete() is None


def test_completing_twice_does_not_create_duplicate():
    task = Task("Feed", at(8), frequency=Frequency.DAILY)
    assert task.mark_complete(today=DAY.date()) is not None
    assert task.mark_complete(today=DAY.date()) is None


def test_late_completion_recurs_from_today():
    task = Task("Feed", at(8), frequency=Frequency.DAILY)
    today = (DAY + timedelta(days=3)).date()

    nxt = task.mark_complete(today=today)

    assert nxt.time.date() == today + timedelta(days=1)
    assert nxt.time.time() == task.time.time()


def test_scheduler_complete_task_adds_next_to_same_pet():
    sched, rex, mia = make_scheduler()
    task = Task("Feed", at(8), frequency=Frequency.DAILY)
    rex.add_task(task)

    nxt = sched.complete_task(task)

    assert len(rex.tasks) == 2
    assert nxt in rex.tasks
    assert nxt.pet_name == "Rex"
    assert nxt.time == at(8, day=DAY + timedelta(days=1))
    assert mia.tasks == []


# --- conflict detection ---

def test_same_start_time_is_flagged_as_conflict():
    sched, rex, mia = make_scheduler()
    a = Task("Walk", at(9))
    b = Task("Vet", at(9))
    rex.add_task(a)
    mia.add_task(b)

    conflicts = sched.find_conflicts()

    assert len(conflicts) == 1
    assert set(map(id, conflicts[0])) == {id(a), id(b)}


def test_same_pet_duplicate_time_produces_warning():
    sched, rex, _ = make_scheduler()
    rex.add_task(Task("Walk", at(9)))
    rex.add_task(Task("Groom", at(9)))

    warnings = sched.conflict_warnings()

    assert len(warnings) == 1
    assert "same pet" in warnings[0]


def test_different_pet_conflict_warning_scope():
    sched, rex, mia = make_scheduler()
    rex.add_task(Task("Walk", at(9)))
    mia.add_task(Task("Feed", at(9)))

    assert "different pets" in sched.conflict_warnings()[0]


def test_partial_overlap_is_a_conflict():
    sched, rex, _ = make_scheduler()
    rex.add_task(Task("Walk", at(9), duration=30))
    rex.add_task(Task("Groom", at(9, 15), duration=30))

    assert len(sched.find_conflicts()) == 1


def test_back_to_back_tasks_do_not_conflict():
    sched, rex, _ = make_scheduler()
    rex.add_task(Task("Walk", at(9), duration=30))
    rex.add_task(Task("Groom", at(9, 30), duration=30))

    assert sched.find_conflicts() == []
    assert sched.conflict_warnings() == []


def test_completed_tasks_are_ignored_by_default_conflict_check():
    sched, rex, _ = make_scheduler()
    done = Task("Walk", at(9))
    rex.add_task(done)
    rex.add_task(Task("Groom", at(9)))
    done.mark_complete()

    assert sched.find_conflicts() == []


# --- edge cases ---

def test_pet_with_no_tasks_yields_empty_results():
    sched, _, _ = make_scheduler()

    assert sched.get_all_tasks() == []
    assert sched.find_conflicts() == []
    assert sched.generate_schedule() == []
    assert sched.display_plan() == "No tasks scheduled."


def test_filter_by_pet_and_completion():
    sched, rex, mia = make_scheduler()
    walk = Task("Walk", at(8))
    rex.add_task(walk)
    rex.add_task(Task("Feed", at(9)))
    mia.add_task(Task("Play", at(10)))
    walk.mark_complete()

    assert [t.description for t in sched.filter_tasks(pet_name="rex")] == ["Walk", "Feed"]
    assert [t.description for t in sched.filter_tasks(pet_name="Rex", completed=False)] == ["Feed"]
    assert sched.filter_tasks(pet_name="Nobody") == []


def test_generate_schedule_skips_tasks_that_do_not_fit():
    sched, rex, _ = make_scheduler(available_time=30)
    rex.add_task(Task("Walk", at(8), duration=30, priority=Priority.HIGH))
    skipped = Task("Groom", at(9), duration=20, priority=Priority.LOW)
    rex.add_task(skipped)

    plan = sched.generate_schedule()

    assert [t.description for t in plan] == ["Walk"]
    assert sched.skipped == [skipped]
