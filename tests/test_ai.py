import json

import ai_agent
from pawpal_system import Frequency, Pet, Priority, Task
from retriever import life_stage, retrieve
from datetime import datetime


def good_item(**over):
    item = {
        "description": "Morning walk", "start": "07:30", "duration": 30,
        "frequency": "daily", "priority": "high", "source": "dog_adult", "reason": "Dogs need walks.",
    }
    item.update(over)
    return item


def fake_llm(*items):
    return lambda prompt, model: json.dumps({"tasks": list(items)})


# --- retriever ---

def test_life_stage_boundaries():
    assert life_stage(None) is None
    assert life_stage(0.5) == "young"
    assert life_stage(3) == "adult"
    assert life_stage(10) == "senior"


def test_retrieves_species_and_stage_match_first():
    assert retrieve("dog", "labrador", 0.5)[0].id == "dog_young"
    assert retrieve("cat", "", 12)[0].id == "cat_senior"


def test_unknown_species_falls_back_to_general_doc():
    assert [d.id for d in retrieve("other", "axolotl", 2)] == ["general"]


def test_retrieval_is_deterministic():
    assert retrieve("dog", "poodle", 4) == retrieve("dog", "poodle", 4)


# --- parsing / guardrails ---

def test_parse_accepts_valid_output():
    out, rejected = ai_agent.parse_response(json.dumps({"tasks": [good_item()]}), {"dog_adult"}, set())
    assert rejected == 0 and out[0].description == "Morning walk"
    assert out[0].priority == Priority.HIGH and out[0].frequency == Frequency.DAILY


def test_parse_rejects_bad_items_but_keeps_good_ones():
    items = [
        good_item(),
        good_item(description="Bad time", start="25:99"),
        good_item(description="Bad duration", duration=0),
        good_item(description="Ungrounded", source="made_up_doc"),
        good_item(description="Bad enum", priority="urgent"),
        good_item(description="morning walk"),  # duplicate of the first
    ]
    out, rejected = ai_agent.parse_response(json.dumps({"tasks": items}), {"dog_adult"}, set())
    assert [s.description for s in out] == ["Morning walk"]
    assert rejected == 5


def test_parse_skips_tasks_the_pet_already_has():
    out, rejected = ai_agent.parse_response(json.dumps({"tasks": [good_item()]}), {"dog_adult"}, {"morning walk"})
    assert out == [] and rejected == 1


def test_parse_raises_on_non_json():
    try:
        ai_agent.parse_response("not json", {"dog_adult"}, set())
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# --- agent ---

def adult_dog():
    return Pet("Rex", "labrador", species="dog", age_years=4)


def test_suggest_tasks_happy_path_and_to_task():
    result = ai_agent.suggest_tasks(adult_dog(), llm=fake_llm(good_item()))
    assert result.error is None and len(result.suggestions) == 1
    task = result.suggestions[0].to_task()
    assert isinstance(task, Task) and task.time.hour == 7 and task.time.minute == 30 and task.duration == 30


def test_suggest_tasks_retries_once_on_bad_output():
    calls = []

    def flaky(prompt, model):
        calls.append(1)
        return "garbage" if len(calls) == 1 else json.dumps({"tasks": [good_item()]})

    result = ai_agent.suggest_tasks(adult_dog(), llm=flaky)
    assert len(calls) == 2 and result.error is None and result.suggestions


def test_suggest_tasks_reports_error_when_output_never_valid():
    result = ai_agent.suggest_tasks(adult_dog(), llm=lambda p, m: "garbage")
    assert result.suggestions == [] and result.error


def test_suggest_tasks_never_raises_on_api_failure():
    def boom(prompt, model):
        raise ConnectionError("network down")

    result = ai_agent.suggest_tasks(adult_dog(), llm=boom)
    assert result.suggestions == [] and "unavailable" in result.error


def test_prompt_contains_retrieved_docs_and_profile():
    pet = adult_dog()
    pet.add_task(Task("Evening play", datetime(2099, 1, 1, 18)))
    result = ai_agent.suggest_tasks(pet, llm=lambda p, m: captured.append(p) or json.dumps({"tasks": [good_item()]}))
    prompt = captured[0]
    assert result.docs[0].body.splitlines()[0] in prompt  # retrieved text drives the prompt
    assert "labrador" in prompt and "Evening play" in prompt


captured = []


def test_feature_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert ai_agent.is_configured() is False
    result = ai_agent.suggest_tasks(adult_dog())
    assert result.suggestions == [] and "API key" in result.error
