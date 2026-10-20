from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum, IntEnum
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

    def mark_complete(self) -> Optional[Task]:
        """Mark done. Returns the next occurrence for daily/weekly tasks, else None."""
        self.completed = True
        step = _RECURRENCE.get(self.frequency)
        if step is None:
            return None
        return Task(
            description=self.description,
            time=self.time + step,
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
        """Sort the given tasks (default: all) by start time."""
        tasks = self.get_all_tasks() if tasks is None else tasks
        return sorted(tasks, key=lambda t: t.time)

    def filter_tasks(
        self, pet_name: Optional[str] = None, completed: Optional[bool] = None
    ) -> List[Task]:
        """Filter all tasks by pet name and/or completion status."""
        tasks = self.get_all_tasks()
        if pet_name is not None:
            tasks = [t for t in tasks if t.pet_name == pet_name]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        return tasks

    # --- managing ---

    def complete_task(self, task: Task) -> Optional[Task]:
        """Complete a task; recurring tasks are re-added to the same pet."""
        nxt = task.mark_complete()
        if nxt is not None:
            pet = self.owner.get_pet(task.pet_name)
            if pet is not None:
                pet.add_task(nxt)
        return nxt

    def find_conflicts(self, tasks: Optional[List[Task]] = None) -> List[Tuple[Task, Task]]:
        """Pairs of tasks whose time ranges overlap (any pets)."""
        ordered = self.sort_by_time(self.pending_tasks() if tasks is None else tasks)
        return [
            (a, b)
            for i, a in enumerate(ordered)
            for b in ordered[i + 1:]
            if b.time < a.end_time
        ]

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
        for a, b in self.find_conflicts(self.scheduled):
            self.reasoning.append(
                f"Warning: {a.description} ({a.pet_name}) overlaps "
                f"{b.description} ({b.pet_name})."
            )
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
