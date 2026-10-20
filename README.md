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

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

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
