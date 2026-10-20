# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## ✨ Features

- **Multi-pet task tracking** — an owner can have several pets, each with its own tasks (description, start time, duration, priority, repeat frequency). The scheduler reads every pet's tasks at once.
- **Sorting by time** — tasks are ordered chronologically (date and time), with higher priority first when two tasks start together.
- **Filtering** — view tasks by pet (case-insensitive), by status (pending or completed), or both.
- **Priority-based daily schedule** — pending tasks for the chosen day are taken highest priority first (then earlier start, then shorter duration) until the owner's available minutes run out. Anything that doesn't fit is skipped and listed.
- **Conflict warnings** — every pair of overlapping pending tasks is flagged, whether for the same pet or different pets. Back-to-back tasks are not conflicts. Conflicts are warned about, never silently resolved or raised as errors.
- **Daily and weekly recurrence** — completing a daily or weekly task automatically creates the next occurrence (+1 day or +1 week, same time of day). Completing a task twice never creates a duplicate.
- **Explained plans** — every scheduled or skipped task comes with a plain-language reason.
- **Input validation** — durations must be positive and available time can't be negative.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.  The final diagram is in `diagrams/uml_final.mmd`.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
Today's Schedule for Jackson (90 min available)
==================================================
07:30-08:00  Morning walk (Rex)
08:00-08:15  Breakfast (Mia)
18:30-18:50  Play session (Mia)

Reasoning
--------------------------------------------------
Scheduled Morning walk (Rex): HIGH priority, 30 min, 60 min left.
Scheduled Breakfast (Mia): HIGH priority, 15 min, 45 min left.
Scheduled Play session (Mia): MEDIUM priority, 20 min, 25 min left.
Skipped Grooming (Rex): needs 45 min, only 25 left.
```

## Implementation summary

The backend logic lives in `pawpal_system.py`, is demonstrated from the terminal with `main.py`, and is used by the Streamlit UI in `app.py`.

There are four main classes:

- **Task**: one activity, like a walk or a feeding. It stores a description, start time, duration, how often it repeats (once, daily, weekly), a priority, and whether it's done. When you complete a daily or weekly task, `mark_complete()` hands back the next one.
- **Pet**: a name and breed plus its own list of tasks.
- **Owner**: has a list of pets and how many minutes they have free in a day. `get_all_tasks()` collects every pet's tasks into one list.
- **Scheduler**: the part that makes the plan. It gets tasks through `owner.get_all_tasks()` instead of looking at one pet, so it can plan for all of them at once. It sorts and filters tasks, flags overlapping times, and builds the day's schedule by taking the highest priority tasks first until the owner runs out of time. Anything that doesn't fit gets skipped, and it keeps a note of why.

The Owner has Pets, the Pets have Tasks, and the Scheduler reads all of those tasks through the Owner and decides what fits into the day.

## Smarter Scheduling

Algorithms added in `pawpal_system.py`, demonstrated by `main.py`:

- **Sorting by time** — `Scheduler.sort_by_time()` orders tasks chronologically with `sorted(key=lambda t: (t.time, -t.priority))`, so higher priority wins ties.
- **Filtering** — `Scheduler.filter_tasks(pet_name=None, completed=None)` filters by pet (case-insensitive) and/or completion status; both filters combine. `Scheduler.pending_tasks()` is a shortcut for not-completed tasks.
- **Conflict detection** — `Scheduler.find_conflicts()` sweeps the time-sorted pending tasks and returns every overlapping pair (same pet or different pets), stopping early once no later task can overlap. `Scheduler.conflict_warnings()` turns those pairs into warning strings instead of raising, and `generate_schedule()` appends them to the reasoning. Overlaps are warned about, not automatically resolved.
- **Recurring tasks** — `Task.mark_complete()` returns the next daily or weekly occurrence, due at max(task date, today) plus a `timedelta` of 1 day or 1 week, keeping the time of day. `Scheduler.complete_task()` adds it to the same pet. Completing an already-completed task creates no duplicate.

## 🧪 Testing PawPal+

```bash
python -m pytest
```

The suite in `tests/test_pawpal.py` (22 tests) covers:

- **Sorting** — chronological order across pets, priority tie-breaks, multi-day ordering, and an empty task list.
- **Recurrence** — daily tasks create a next-day task, weekly tasks recur a week later, one-off tasks don't recur, completing twice creates no duplicate, late completion recurs from today, and `Scheduler.complete_task` adds the new task to the right pet.
- **Conflict detection** — same-time tasks (same pet and different pets), partial overlaps, back-to-back tasks (not a conflict), and completed tasks being ignored.
- **Edge cases** — pets with no tasks, invalid durations, filtering by pet and status, and tasks skipped when they don't fit the available time.

Sample test output:

```
============================= test session starts ==============================
platform darwin -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/jacksonaltman/Desktop/ai110-module2show-pawpal-starter
collected 22 items

tests/test_pawpal.py ......................                              [100%]

============================== 22 passed in 0.01s ==============================
```

**Confidence Level: ⭐⭐⭐⭐ (4/5)** — All 22 tests pass and cover the main behaviors and edge cases. However, the tests don't cover the Streamlit UI (`app.py`) or tasks that span midnight, and `Scheduler.complete_task` depends on the real current date.

## 📸 Demo Walkthrough

### Running the app

```bash
streamlit run app.py   # web UI
python main.py         # terminal demo of the same scheduler
```

### What you can do in the UI

- **Owner** — set your name and how many minutes you have available today.
- **Pets** — add pets (name and breed); a table shows each pet and its task count.
- **Tasks** — add a task for a pet with a start time, duration, repeat frequency (once, daily, weekly) and priority.
- **All tasks** — see every task sorted by time, and filter by pet and/or status.
- **Mark complete** — finish a task; daily and weekly tasks automatically get a next occurrence.
- **Generate schedule** — build today's plan, with skipped tasks and the reasoning behind it.

### Example workflow

1. Set the owner to "Jordan" with 90 minutes available.
2. Add two pets, Rex (Lab) and Mia (Tabby).
3. Add "Morning walk" (07:30, 30 min, high, daily) for Rex and "Vet call" (07:30, 20 min, medium) for Rex.
4. A yellow conflict warning appears immediately: the walk and the vet call overlap, with a tip to move the call to 08:00 or later.
5. Add a few more tasks (breakfast and a play session for Mia, grooming for Rex). The task table stays sorted by time, and the pet filter narrows it to one animal.
6. Mark "Morning walk" complete. A message says its next daily occurrence is scheduled for tomorrow at 07:30.
7. Click **Generate schedule** to see today's plan, a "used X of 90 minutes" summary, any skipped tasks, and the "Why this plan?" explanation.

### Scheduler behaviors shown

- **Sorting** — tasks added out of order are displayed chronologically.
- **Filtering** — by pet and by completed or pending.
- **Conflict warnings** — overlapping tasks are flagged for the same pet and across pets, before and after generating a plan.
- **Recurrence** — completing a recurring task queues the next one.
- **Skipping** — a task that no longer fits in the available time is skipped and explained.

### Sample CLI output (`python main.py`)

```

As added (unsorted)
--------------------------------------------------
[ ] Mon 17:00  Grooming (Rex)
[ ] Mon 07:30  Morning walk (Rex)
[ ] Mon 07:30  Vet call (Rex)
[ ] Mon 18:40  Training (Rex)
[ ] Mon 18:30  Play session (Mia)
[x] Mon 08:00  Breakfast (Mia)
[ ] Tue 08:00  Breakfast (Mia)

Sorted by time
--------------------------------------------------
[ ] Mon 07:30  Morning walk (Rex)
[ ] Mon 07:30  Vet call (Rex)
[x] Mon 08:00  Breakfast (Mia)
[ ] Mon 17:00  Grooming (Rex)
[ ] Mon 18:30  Play session (Mia)
[ ] Mon 18:40  Training (Rex)
[ ] Tue 08:00  Breakfast (Mia)

Rex's tasks
--------------------------------------------------
[ ] Mon 17:00  Grooming (Rex)
[ ] Mon 07:30  Morning walk (Rex)
[ ] Mon 07:30  Vet call (Rex)
[ ] Mon 18:40  Training (Rex)

Completed tasks
--------------------------------------------------
[x] Mon 08:00  Breakfast (Mia)

Pending tasks for Mia
--------------------------------------------------
[ ] Mon 18:30  Play session (Mia)
[ ] Tue 08:00  Breakfast (Mia)

Conflict check (all pending tasks)
--------------------------------------------------
Warning (same pet): Morning walk (Rex, 07:30-08:00) overlaps Vet call (Rex, 07:30-07:50).
Warning (different pets): Play session (Mia, 18:30-18:50) overlaps Training (Rex, 18:40-19:00).

Today's Schedule for Jackson (90 min available)
==================================================
07:30-08:00  Morning walk (Rex)
07:30-07:50  Vet call (Rex)
18:30-18:50  Play session (Mia)
18:40-19:00  Training (Rex)

Reasoning
--------------------------------------------------
Scheduled Morning walk (Rex): HIGH priority, 30 min, 60 min left.
Scheduled Vet call (Rex): MEDIUM priority, 20 min, 40 min left.
Scheduled Play session (Mia): MEDIUM priority, 20 min, 20 min left.
Skipped Grooming (Rex): needs 45 min, only 20 left.
Scheduled Training (Rex): LOW priority, 20 min, 0 min left.
Warning (same pet): Morning walk (Rex, 07:30-08:00) overlaps Vet call (Rex, 07:30-07:50).
Warning (different pets): Play session (Mia, 18:30-18:50) overlaps Training (Rex, 18:40-19:00).
```
