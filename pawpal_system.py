from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Pet:
    name: str
    breed: str


@dataclass
class Task:
    name: str
    category: str
    duration: int  # minutes
    priority: str  # e.g. "low", "medium", "high"


@dataclass
class Owner:
    name: str
    available_time: int  # minutes available per day
    pets: List[Pet] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass


@dataclass
class Plan:
    owner: Owner
    time_limit: int
    tasks: List[Task] = field(default_factory=list)

    def generate_schedule(self) -> None:
        pass

    def display_plan(self) -> None:
        pass

    def explain_reasoning(self) -> str:
        pass
