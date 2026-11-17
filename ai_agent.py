"""AI task suggestions: retrieve care docs, ask Gemini to turn them into tasks, validate.

Flow: Pet profile -> retriever.retrieve() -> prompt (profile + docs) -> Gemini JSON
-> guardrails (schema, grounding in retrieved docs, de-duplication) -> Suggestion list.
Nothing is added to a pet's schedule here; the UI shows suggestions for human review.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, List, Optional

from pawpal_system import Frequency, Pet, Priority, Task
from retriever import Doc, retrieve

logger = logging.getLogger("pawpal.agent")

DEFAULT_MODEL = "gemini-3.8-flash"
MAX_SUGGESTIONS = 8
MAX_ATTEMPTS = 2  # one retry if the model returns unusable output
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def setup_logging(logfile: str = "pawpal.log") -> None:
    """Log to console and a rotating file. Safe to call more than once."""
    root = logging.getLogger("pawpal")
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    for handler in (
        logging.StreamHandler(),
        RotatingFileHandler(Path(__file__).parent / logfile, maxBytes=500_000, backupCount=2),
    ):
        handler.setFormatter(fmt)
        root.addHandler(handler)


def api_key() -> Optional[str]:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or None


def is_configured() -> bool:
    """True if a Gemini key is available. The UI hides the feature otherwise."""
    return api_key() is not None


@dataclass
class Suggestion:
    description: str
    start: str  # "HH:MM"
    duration: int
    frequency: Frequency
    priority: Priority
    source: str  # id of the retrieved doc this came from
    reason: str

    def to_task(self, day: Optional[date] = None) -> Task:
        hour, minute = map(int, self.start.split(":"))
        when = datetime.combine(day or date.today(), datetime.min.time()).replace(hour=hour, minute=minute)
        return Task(
            description=self.description,
            time=when,
            duration=self.duration,
            frequency=self.frequency,
            priority=self.priority,
        )


@dataclass
class SuggestionResult:
    suggestions: List[Suggestion] = field(default_factory=list)
    docs: List[Doc] = field(default_factory=list)  # what was retrieved (shown to the user)
    error: Optional[str] = None
    rejected: int = 0  # items the guardrails dropped


def build_prompt(pet: Pet, docs: List[Doc]) -> str:
    age = f"{pet.age_years:g} years" if pet.age_years is not None else "unknown"
    context = "\n\n".join(f"[doc id: {d.id}] {d.title}\n{d.body}" for d in docs)
    existing = ", ".join(t.description for t in pet.tasks) or "none"
    return f"""You help a pet owner build a daily care routine.

PET PROFILE
- name: {pet.name}
- species: {pet.species}
- breed: {pet.breed}
- age: {age}
- tasks already scheduled: {existing}

REFERENCE DOCS (use ONLY these as your source of care guidance)
{context}

Suggest between 3 and {MAX_SUGGESTIONS} recurring daily tasks for this pet, based on the reference docs.
Do not repeat tasks already scheduled. Spread start times sensibly across the day without overlaps.

Respond with JSON only, in exactly this shape:
{{"tasks": [{{"description": "short task name",
  "start": "HH:MM" (24-hour),
  "duration": minutes as an integer between 1 and 240,
  "frequency": "once" | "daily" | "weekly",
  "priority": "low" | "medium" | "high",
  "source": "the doc id this task comes from",
  "reason": "one sentence citing the guidance"}}]}}"""


def parse_response(text: str, valid_sources: set[str], existing: set[str]) -> tuple[List[Suggestion], int]:
    """Validate model output. Returns (valid suggestions, number rejected).

    Raises ValueError if the output isn't JSON of the expected top-level shape.
    """
    try:
        data = json.loads(text)
        items = data["tasks"]
        if not isinstance(items, list):
            raise TypeError("'tasks' is not a list")
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"Model output is not valid task JSON: {exc}") from exc

    suggestions: List[Suggestion] = []
    rejected = 0
    seen = set(existing)
    for item in items:
        try:
            description = str(item["description"]).strip()
            start = str(item["start"]).strip()
            duration = int(item["duration"])
            frequency = Frequency(str(item["frequency"]).lower())
            priority = Priority[str(item["priority"]).upper()]
            source = str(item["source"]).strip()
            reason = str(item.get("reason", "")).strip()
            if not description or len(description) > 80:
                raise ValueError("bad description")
            if not _TIME.match(start):
                raise ValueError(f"bad time {start!r}")
            if not 1 <= duration <= 240:
                raise ValueError(f"bad duration {duration}")
            if source not in valid_sources:  # grounding: must cite a doc we actually retrieved
                raise ValueError(f"source {source!r} was not retrieved")
            if description.lower() in seen:
                raise ValueError("duplicate task")
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            rejected += 1
            logger.warning("Rejected suggestion %r: %s", item, exc)
            continue
        seen.add(description.lower())
        suggestions.append(Suggestion(description, start, duration, frequency, priority, source, reason))
        if len(suggestions) == MAX_SUGGESTIONS:
            break
    return suggestions, rejected


def _gemini_call(prompt: str, model: str) -> str:
    """Call Gemini and return the raw text. Imported lazily so tests/offline use don't need the SDK."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key())
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
    )
    return response.text or ""


def suggest_tasks(
    pet: Pet,
    k: int = 3,
    model: Optional[str] = None,
    llm: Optional[Callable[[str, str], str]] = None,
) -> SuggestionResult:
    """Retrieve docs for the pet and ask the model for validated task suggestions.

    `llm(prompt, model) -> text` is injectable so tests and the evaluator can run without the network.
    Never raises: failures come back in `result.error`.
    """
    result = SuggestionResult()
    result.docs = retrieve(pet.species, pet.breed, pet.age_years, k=k)
    if not result.docs:
        result.error = "No relevant care guidance found for this pet."
        logger.warning("No docs retrieved for %s (%s)", pet.name, pet.species)
        return result

    if llm is None:
        if not is_configured():
            result.error = "No Gemini API key configured (set GEMINI_API_KEY)."
            return result
        llm = _gemini_call
    model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    prompt = build_prompt(pet, result.docs)
    valid_sources = {d.id for d in result.docs}
    existing = {t.description.lower() for t in pet.tasks}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            text = llm(prompt, model)
            suggestions, rejected = parse_response(text, valid_sources, existing)
        except ValueError as exc:  # bad JSON: retry once
            logger.warning("Attempt %d/%d for %s: %s", attempt, MAX_ATTEMPTS, pet.name, exc)
            result.error = "The AI returned output we couldn't use. Try again."
            continue
        except Exception as exc:  # network/auth/quota: don't retry blindly, don't crash the app
            logger.error("Model call failed for %s: %s", pet.name, exc)
            detail = str(exc).split(". ")[0][:120]  # e.g. "404 NOT_FOUND" / "403 PERMISSION_DENIED"
            result.error = f"The AI service is unavailable ({detail}). Your schedule is unchanged. See pawpal.log."
            return result
        result.rejected += rejected
        if suggestions:
            result.suggestions, result.error = suggestions, None
            logger.info("%d suggestion(s) for %s (%d rejected)", len(suggestions), pet.name, rejected)
            return result
        result.error = "The AI didn't return any usable tasks. Try again."
    return result
