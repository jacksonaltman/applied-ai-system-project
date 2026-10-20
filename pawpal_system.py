from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import List, Optional
from uuid import uuid4


class Priority(IntEnum):
    """Ordered so that higher value means more important (sorts correctly)."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Category(str, Enum):
    FEEDING = "feeding"
    WALK = "walk"
    MEDICATION = "medication"
    GROOMING = "grooming"
    PLAY = "play"
    OTHER = "other"


@dataclass
class Pet:
    name: str
    breed: str
    id: str = field(default_factory=lambda: uuid4().hex)  # names may repeat


@dataclass
class Task:
    name: str
    category: Category
    duration: int  # minutes, must be > 0
    priority: Priority
    pet: Pet

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError("Task duration must be greater than 0 minutes")


@dataclass
class Owner:
    name: str
    available_time: int  # minutes available per day, must be >= 0
    pets: List[Pet] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.available_time < 0:
            raise ValueError("available_time cannot be negative")

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, pet: Pet) -> None:
        """Also removes the pet's tasks."""
        pass

    def add_task(self, task: Task) -> None:
        """Task's pet must already belong to this owner."""
        pass

    def remove_task(self, task: Task) -> None:
        pass


@dataclass
class ScheduledTask:
    task: Task
    start_minute: int  # minutes from the start of the plan

    @property
    def end_minute(self) -> int:
        return self.start_minute + self.task.duration


@dataclass
class Plan:
    owner: Owner
    time_limit: Optional[int] = None  # None -> use owner.available_time
    scheduled: List[ScheduledTask] = field(default_factory=list)
    skipped: List[Task] = field(default_factory=list)
    reasoning: List[str] = field(default_factory=list)  # filled by generate_schedule

    @property
    def effective_time_limit(self) -> int:
        if self.time_limit is not None:
            return self.time_limit
        return self.owner.available_time

    def generate_schedule(self) -> None:
        """Pick from owner.tasks into `scheduled`/`skipped`, recording `reasoning`.

        Greedy: priority (high first), then shorter duration, then name.
        Tasks longer than the limit, or that no longer fit, go to `skipped`.
        """
        pass

    def display_plan(self) -> str:
        """Return the schedule as text so the UI/tests can use it."""
        pass

    def explain_reasoning(self) -> str:
        """Return reasoning recorded by generate_schedule()."""
        pass
