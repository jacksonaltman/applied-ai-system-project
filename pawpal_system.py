from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum, IntEnum
from itertools import islice
from typing import List, Optional, Tuple
from uuid import uuid4


class Priority(IntEnum):
    """Ordered so that higher value means more important (sorts correctly)."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Frequency(str, Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


_RECURRENCE = {
    Frequency.DAILY: timedelta(days=1),
    Frequency.WEEKLY: timedelta(weeks=1),
}


@dataclass
class Task:
    """A single activity for a pet."""
    description: str
    time: datetime  # when the task starts
    duration: int = 15  # minutes, must be > 0
    frequency: Frequency = Frequency.ONCE
    priority: Priority = Priority.MEDIUM
    completed: bool = False
    pet_name: str = ""  # set by Pet.add_task

    def __post_init__(self) -> None:
        """Reject a non-positive duration."""
        if self.duration <= 0:
            raise ValueError("Task duration must be greater than 0 minutes")

    @property
    def end_time(self) -> datetime:
        """When the task finishes."""
        return self.time + timedelta(minutes=self.duration)

    def mark_complete(self, today: Optional[date] = None) -> Optional[Task]:
        """Mark done. Returns the next occurrence for daily/weekly tasks, else None.

        The next due date is the later of the task's own date and today, plus
        one timedelta step (1 day or 1 week), keeping the original time of day.
        A task completed on time or late therefore recurs at today + step; one
        completed early recurs at its due date + step. Completing a task that
        is already complete returns None, so no duplicate is created.
        """
        if self.completed:
            return None
        self.completed = True
        step = _RECURRENCE.get(self.frequency)
        if step is None:
            return None
        base = max(self.time.date(), today or date.today())
        next_time = datetime.combine(base, self.time.time()) + step
        return Task(
            description=self.description,
            time=next_time,
            duration=self.duration,
            frequency=self.frequency,
            priority=self.priority,
        )


@dataclass
class Pet:
    name: str
    breed: str
    id: str = field(default_factory=lambda: uuid4().hex)  # names may repeat
    tasks: List[Task] = field(default_factory=list)
    species: str = "unknown"  # used by the AI retriever, e.g. "dog", "cat"
    age_years: Optional[float] = None  # used to pick a life stage (young/adult/senior)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet and tag it with the pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet."""
        self.tasks.remove(task)


@dataclass
class Owner:
    name: str
    available_time: int  # minutes available per day, must be >= 0
    pets: List[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Reject a negative available_time."""
        if self.available_time < 0:
            raise ValueError("available_time cannot be negative")

    def add_pet(self, pet: Pet) -> None:
        """Add a pet, rejecting duplicates."""
        if any(p.id == pet.id for p in self.pets):
            raise ValueError(f"{pet.name} is already owned by {self.name}")
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner."""
        self.pets.remove(pet)

    def get_pet(self, name: str) -> Optional[Pet]:
        """Find a pet by name, or None."""
        return next((p for p in self.pets if p.name == name), None)

    def get_all_tasks(self) -> List[Task]:
        """Every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]


class Scheduler:
    """The brain: reads every pet's tasks via Owner.get_all_tasks()."""

    def __init__(self, owner: Owner) -> None:
        """Create a scheduler for an owner with empty results."""
        self.owner = owner
        self.scheduled: List[Task] = []
        self.skipped: List[Task] = []
        self.reasoning: List[str] = []

    # --- retrieving / organizing ---

    def get_all_tasks(self) -> List[Task]:
        """Every task across all pets, via the owner."""
        return self.owner.get_all_tasks()

    def pending_tasks(self) -> List[Task]:
        """Tasks not yet completed."""
        return [t for t in self.get_all_tasks() if not t.completed]

    def sort_by_time(self, tasks: Optional[List[Task]] = None) -> List[Task]:
        """Sort the given tasks (default: all) by start time, then priority.

        Task.time is a datetime, so it compares chronologically. If times were
        "HH:MM" strings, key=lambda t: t.time would also work, because
        zero-padded 24-hour strings sort lexically in time order.
        """
        tasks = self.get_all_tasks() if tasks is None else tasks
        return sorted(tasks, key=lambda t: (t.time, -t.priority))

    def filter_tasks(
        self, pet_name: Optional[str] = None, completed: Optional[bool] = None
    ) -> List[Task]:
        """Filter all tasks by pet name and/or completion status.

        Args:
            pet_name: Keep only this pet's tasks (case-insensitive). None skips this filter.
            completed: True for done tasks, False for pending. None skips this filter.

        Returns:
            Matching tasks in their original order; both filters combine with AND.
        """
        tasks = self.get_all_tasks()
        if pet_name is not None:
            tasks = [t for t in tasks if t.pet_name.lower() == pet_name.lower()]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        return tasks

    # --- managing ---

    def complete_task(self, task: Task) -> Optional[Task]:
        """Complete a task and queue its next occurrence if it recurs.

        Delegates the date math to Task.mark_complete(). A new daily/weekly task
        is added to the same pet; returns it, or None for one-off tasks or
        tasks that were already complete.
        """
        nxt = task.mark_complete()
        if nxt is not None:
            pet = self.owner.get_pet(task.pet_name)
            if pet is not None:
                pet.add_task(nxt)
        return nxt

    def find_conflicts(self, tasks: Optional[List[Task]] = None) -> List[Tuple[Task, Task]]:
        """Pairs of tasks whose time ranges overlap (same pet or different pets).

        Sweeps the time-sorted list and stops comparing a task as soon as a
        later one starts at or after its end, since nothing after can overlap.
        """
        ordered = self.sort_by_time(self.pending_tasks() if tasks is None else tasks)
        conflicts = []
        for i, a in enumerate(ordered):
            for b in islice(ordered, i + 1, None):  # no list copy
                if b.time >= a.end_time:
                    break
                conflicts.append((a, b))
        return conflicts

    def conflict_warnings(self, tasks: Optional[List[Task]] = None) -> List[str]:
        """Human-readable warning per overlapping pair; never raises."""
        warnings = []
        for a, b in self.find_conflicts(tasks):
            scope = "same pet" if a.pet_name == b.pet_name else "different pets"
            warnings.append(
                f"Warning ({scope}): {a.description} ({a.pet_name}, "
                f"{a.time:%H:%M}-{a.end_time:%H:%M}) overlaps "
                f"{b.description} ({b.pet_name}, {b.time:%H:%M}-{b.end_time:%H:%M})."
            )
        return warnings

    def generate_schedule(self, day: Optional[date] = None) -> List[Task]:
        """Fit pending tasks (all pets) into owner.available_time.

        Greedy: priority (high first), then earlier time, shorter duration,
        description. Tasks that no longer fit go to `skipped`.
        """
        self.scheduled, self.skipped, self.reasoning = [], [], []
        candidates = self.pending_tasks()
        if day is not None:
            candidates = [t for t in candidates if t.time.date() == day]
        candidates.sort(key=lambda t: (-t.priority, t.time, t.duration, t.description))

        remaining = self.owner.available_time
        for task in candidates:
            label = f"{task.description} ({task.pet_name})"
            if task.duration <= remaining:
                remaining -= task.duration
                self.scheduled.append(task)
                self.reasoning.append(
                    f"Scheduled {label}: {task.priority.name} priority, "
                    f"{task.duration} min, {remaining} min left."
                )
            else:
                self.skipped.append(task)
                self.reasoning.append(
                    f"Skipped {label}: needs {task.duration} min, only {remaining} left."
                )

        self.scheduled = self.sort_by_time(self.scheduled)
        self.reasoning.extend(self.conflict_warnings(self.scheduled))
        return self.scheduled

    def display_plan(self) -> str:
        """Format the scheduled tasks as text."""
        if not self.scheduled:
            return "No tasks scheduled."
        return "\n".join(
            f"{t.time:%H:%M}-{t.end_time:%H:%M}  {t.description} ({t.pet_name})"
            for t in self.scheduled
        )

    def explain_reasoning(self) -> str:
        """Return why each task was scheduled or skipped."""
        return "\n".join(self.reasoning) or "No schedule generated yet."
