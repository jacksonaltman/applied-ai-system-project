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
7. Refine UML so it matches what you actually built.

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

So far I've built the backend logic in `pawpal_system.py` and tested it from the terminal with `main.py`. The Streamlit UI isn't connected yet.

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

**Confidence Level:** — Pretty high. All 22 tests pass and cover the main behaviors and edge cases. However, the tests don't cover the Streamlit UI (`app.py`) or tasks that span midnight, and `Scheduler.complete_task` depends on the real current date.

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | | e.g., by priority, duration |
| Filtering | | e.g., skip tasks if time runs out |
| Conflict handling | | e.g., overlapping time slots |
| Recurring tasks | | e.g., daily vs. weekly |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
