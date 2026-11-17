# 🐾 PetCarePro

**A pet-care planner that drafts a care routine from vetted guides and lets you approve it before it touches your schedule.**

PetCarePro extends my Module 2 project, **PawPal+**. PawPal+ was a Streamlit app where a busy pet owner enters their pets and care tasks (walks, feedings, meds, grooming). It then builds a daily plan: it sorts tasks by time and priority, warns about overlaps, repeats daily and weekly tasks, and fits everything into the owner's available minutes with a plain-language explanation. It was entirely rule-based, so the owner still had to know *what* a pet needs. PetCarePro adds an AI layer that answers that question.

## What it does and why it matters

New pet owners often don't know what a 6-month-old lab puppy needs compared with a 12-year-old cat, so their schedule is only as good as their guesses. PetCarePro fixes that with **Retrieval-Augmented Generation (RAG)**:

1. You enter a pet's species, breed and age.
2. The app **retrieves** the relevant care guides from a local knowledge base.
3. Gemini **turns those guides into concrete tasks** (name, start time, duration, priority, which guide it came from).
4. Guardrails validate the output, and **you approve each task** before it is added.
5. The original scheduler then handles conflicts, priorities and the daily plan.

The AI is not a chatbot bolted on the side. Its output becomes real `Task` objects that flow through the same conflict detection and scheduling as hand-entered tasks.

## Architecture overview

The full diagram is in [`diagrams/system_diagram.mmd`](diagrams/system_diagram.mmd) (Mermaid). In short:

```
Owner enters pet profile (species, breed, age)
        │
        ▼
 Retriever (retriever.py) ──reads──▶ knowledge/*.md  (12 care guides)
        │ top-3 guides
        ▼
 AI agent (ai_agent.py): prompt = profile + guides ──▶ Gemini ──▶ JSON tasks
        │
        ▼
 Guardrails: schema check · must cite a retrieved guide · de-duplicate · retry once · log
        │ valid suggestions
        ▼
 HUMAN REVIEW (Streamlit checklist: approve / reject each task)
        │ approved tasks
        ▼
 Scheduler (pawpal_system.py): sort · filter · conflict detection · daily plan
```

| Component | File | Role |
|---|---|---|
| Domain model + scheduler | `pawpal_system.py` | Owner, Pet, Task, Scheduler (carried over from PawPal+) |
| Retriever | `retriever.py` | Keyword scoring of guides by species, life stage and breed |
| Knowledge base | `knowledge/` | 12 short markdown care guides |
| AI agent | `ai_agent.py` | Prompt building, Gemini call, validation, retry, logging |
| UI | `app.py` | Streamlit app, including the human-review step |
| Evaluator | `evaluate.py` | Retrieval hit rate and live schema pass rate |
| Tests | `tests/` | 36 pytest tests (22 scheduler, 14 AI) |

**Where humans and tests check the AI:** the owner reviews every suggestion before it is saved; pytest covers the scheduler and the guardrails; the evaluator measures retrieval and output validity.

## Setup instructions

Requires Python 3.10+.

```bash
git clone <this-repo-url> && cd applied-ai-system-final
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py               # core planner; AI button is hidden without a key
```

To enable the AI feature, get a Gemini API key from [Google AI Studio](https://aistudio.google.com/) and set it before launching:

```bash
export GEMINI_API_KEY="your-key"          # PowerShell: $env:GEMINI_API_KEY="your-key"
export GEMINI_MODEL="gemini-3.8-flash"    # optional; this is the default
streamlit run app.py
```

Other commands:

```bash
python -m pytest        # run all tests (no API key or network needed)
python evaluate.py      # retrieval hit rate; also live schema pass rate if a key is set
python main.py          # terminal demo of the scheduler
```

Logs go to the console and `pawpal.log`.

## Sample interactions

**1. Live Gemini suggestion** *(a 6-month-old labrador)*

Review suggestions for Dog and tick the ones you want:


07:00 · Morning meal (15 min, daily, high)
Why: Puppies require 3 meals a day spaced roughly 5-6 hours apart. (source: dog_young)


07:30 · Morning walk and play (15 min, daily, medium)
Why: Puppies need several short walks or play sessions of 10-15 minutes each while avoiding long runs. (source: dog_young)


12:30 · Midday meal (15 min, daily, high)
Why: Feeding 3 meals daily spaced roughly 5-6 hours apart supports consistent puppy growth. (source: dog_young)


14:00 · Basic obedience training (10 min, daily, medium)
Why: Daily training in 5-10 minute sessions helps teach sit, recall, and leash manners. (source: dog_young)


18:00 · Evening meal (15 min, daily, high)
Why: Providing the third scheduled meal of the day fulfills the recommended 3-meal feeding plan. (source: dog_young)


18:30 · Evening play session (15 min, daily, medium)
Why: Short play sessions of 10-15 minutes allow puppies to exercise safely while joints develop. (source: dog_young)


19:30 · Socialization and handling practice (10 min, daily, medium)
Why: Daily 10-minute socialization and gentle handling practice is essential for young puppies. (source: dog_young)

**2. Retrieval picks guides by species and life stage** *(real output, no key needed)*

| Input pet | Guides retrieved (in order) |
|---|---|
| dog, labrador, 0.5 years | `dog_young`, `dog_adult`, `dog_senior` |
| cat, persian, 12 years | `cat_senior`, `cat_adult`, `cat_young` |
| axolotl, axolotl, 2 years (no guide exists) | `general` |

For the puppy, the prompt sent to Gemini contains the guide text itself, so the model must work from it:

```
PET PROFILE
- name: Biscuit
- species: dog
- breed: labrador
- age: 0.5 years
- tasks already scheduled: none

REFERENCE DOCS (use ONLY these as your source of care guidance)
[doc id: dog_young] Puppy care basics
- Feed 3 meals a day (about 15 min each), spaced roughly 5-6 hours apart.
- Potty break after every meal, nap, and play session; at minimum every 2 hours (10 min).
...
```

**3. Guardrails reject unsafe model output** *(real output from the validator)*

Given a model reply with three tasks, one valid, one with start time `25:99`, and one citing a guide that was never retrieved (`invented_doc`):

```
accepted: ['Morning walk']    rejected: 2
```

With no API key configured the app does not crash: the AI section shows *"AI task suggestions are off. Set the GEMINI_API_KEY environment variable…"* and the rest of the planner works normally. If the API fails, the UI shows the reason (for example `404 NOT_FOUND`) and the schedule is left unchanged.

**4. Evaluator** *(real output)*

```
Retrieval hit rate (top-3)
  PASS  dog/labrador/0.5y -> expected dog_young, got ['dog_young', 'dog_adult', 'dog_senior']
  ...
  PASS  other/axolotl/2y -> expected general, got ['general']
  => 12/12 = 100%
```

## Reproducible execution evidence

Everything below was produced by running the command shown, from the repo root, with no API key set (so it is fully reproducible offline). The raw output is saved in [`logs/`](logs/). The live Gemini run is Sample interaction 1 above.

### 1. Run the full test suite

```bash
python -m pytest -v        # saved to logs/pytest_output.txt
```

```
tests/test_ai.py::test_parse_rejects_bad_items_but_keeps_good_ones PASSED
tests/test_ai.py::test_suggest_tasks_retries_once_on_bad_output PASSED
tests/test_ai.py::test_suggest_tasks_never_raises_on_api_failure PASSED
tests/test_ai.py::test_prompt_contains_retrieved_docs_and_profile PASSED
tests/test_ai.py::test_feature_disabled_without_api_key PASSED
...
============================== 36 passed in 0.02s ==============================
```

### 2. Measure retrieval reliability

```bash
python evaluate.py         # saved to logs/evaluate_output.txt and evaluation_results.md
```

```
Retrieval hit rate (top-3)
  PASS  dog/labrador/0.5y -> expected dog_young, got ['dog_young', 'dog_adult', 'dog_senior']
  PASS  cat/siamese/14y -> expected cat_senior, got ['cat_senior', 'cat_adult', 'cat_young']
  PASS  rabbit/holland lop/2y -> expected rabbit, got ['rabbit', 'general']
  PASS  other/axolotl/2y -> expected general, got ['general']
  ... (12 profiles in total)
  => 12/12 = 100%

Schema pass rate (live model, 3 run(s) per profile)
  SKIPPED: set GEMINI_API_KEY to run this part.
```

With `GEMINI_API_KEY` set, the second block runs the live model 3 times for each of 6 profiles and reports how many runs produced valid output.

### 3. Guardrail demo (input, output, and pass/fail)

```bash
python demo_guardrails.py  # saved to logs/guardrail_demo.txt
```

The script runs the real pipeline against a **hand-written model reply** containing 2 good tasks and 5 bad ones, plus two failure modes. The reply is scripted, not AI-generated, so the guardrail behavior is identical on every run.

```
INPUT pet: Biscuit dog labrador 0.5y | existing tasks: ['Evening play']
RETRIEVED guides: ['dog_young', 'dog_adult', 'dog_senior']
MODEL returned 7 tasks -> 2 accepted, 5 rejected
  ACCEPTED  07:00  Morning meal (15 min, daily, high) source=dog_young
  ACCEPTED  09:30  Potty break (10 min, daily, high) source=dog_young

INPUT: model replies with non-JSON garbage on every attempt
  -> The AI returned output we couldn't use. Try again.

INPUT: the model API is down
  -> The AI service is unavailable (network down). Your schedule is unchanged. See pawpal.log.
```

### 4. Reliability and guardrail results

| scenario (input) | expected behavior | observed |
|---|---|---|
| Valid task citing a retrieved guide | accepted | accepted (Morning meal, Potty break) |
| Task already on the pet's schedule ("Evening play") | rejected as duplicate | rejected |
| Impossible start time `25:99` | rejected | rejected |
| Duration `0` | rejected | rejected |
| Source guide that was never retrieved (`invented_guide`) | rejected (not grounded) | rejected |
| Invalid frequency (`hourly`) | rejected | rejected |
| Model returns non-JSON on every attempt | one retry, then friendly error, no crash | friendly error, no crash |
| Model API unavailable | friendly error, schedule unchanged, no crash | friendly error, no crash |
| No API key configured | AI feature hidden, rest of app works | verified by `test_feature_disabled_without_api_key` |
| Total | | 2 accepted / 5 rejected of 7; 36 / 36 tests pass; retrieval 12 / 12 |

## Design decisions and trade-offs

- **RAG over a plain prompt.** Grounding the model in a small set of known guides keeps its advice consistent and traceable: every suggested task cites a guide. The trade-off is that it can only recommend what the knowledge base covers.
- **Keyword retrieval, not embeddings.** Deterministic, zero extra dependencies, easy to test and explain. The cost is that it misses synonyms (it won't connect "pup" to "puppy"), which the age-to-life-stage mapping partly compensates for.
- **Human in the loop.** Nothing is saved until the owner approves it. This costs one extra click but means a bad suggestion can never silently change a care schedule.
- **Guardrails over trust.** Output is schema-validated, must cite a retrieved guide, and is de-duplicated. Invalid items are dropped and logged rather than fixed up, and bad JSON gets exactly one retry to bound cost and latency.
- **AI is optional.** The deterministic scheduler is unchanged and works without a key, so the AI layer can fail without taking the app down. The model call is injectable, which is what lets the tests run offline.
- **Scheduler kept rule-based.** Priorities, conflicts and time budgets are exact problems. Using code for them is more reliable than asking a model.

## Testing summary

36 pytest tests pass, and the AI tests need no network because the model call is faked.

- **Scheduler (22 tests, from PawPal+):** sorting, recurrence, conflict detection, edge cases.
- **AI layer (14 tests):** retrieval ranking and determinism, unknown-species fallback, schema validation, rejection of bad times, durations, enums and ungrounded sources, de-duplication, retry on bad output, no crash on API failure, prompt contains the retrieved guides, feature off without a key.
- **Evaluator:** retrieval hit rate is 12/12. The live schema pass rate is run with `python evaluate.py` once a key is set.

| check | measured by | result |
|---|---|---|
| Scheduler unit tests | `tests/test_pawpal.py` | 22 / 22 pass |
| AI-layer unit tests (faked model, no network) | `tests/test_ai.py` | 14 / 14 pass |
| Retrieval hit rate (top-3) | `python evaluate.py`, 12 labeled profiles | 12 / 12 = 100% |
| Guardrails reject bad model output | `test_parse_rejects_bad_items_but_keeps_good_ones` | 5 / 5 rejected, 1 good kept |
| Schema pass rate on live Gemini output | `python evaluate.py --runs 3` | not yet run (needs a key) |

`python evaluate.py` writes the full per-case table to [`evaluation_results.md`](evaluation_results.md). The per-test log and a deeper discussion are in [`model_card.md`](model_card.md).

**What worked:** injecting the model call made the whole agent testable without a network. The evaluator also caught a real bug (below).

**What didn't, and what I learned:**
- The retrieval evaluator's output showed a rabbit's top-3 guides included `cat_adult` and `dog_adult`: the life-stage bonus was applied even when the species didn't match. Fixed by scoring life stage only within the matching species.
- The first live call failed with `404 NOT_FOUND` because the default Gemini model had been retired for new users. The error was swallowed into a generic message, so I changed the UI to show the API's reason. Model IDs are configuration, not constants: it is now overridable with `GEMINI_MODEL`.
- Not covered: the Streamlit UI itself, tasks spanning midnight, and the quality (not just validity) of live model output, which is judged by the human reviewer.

## Reflection

This project taught me that most of the work in an AI feature is everything around the model call: deciding what the model is allowed to see, checking what it returns, and keeping a human in control of the result. The model was the easiest part to swap and the hardest to trust, so the reliable pieces (retrieval, validation, scheduling) did the heavy lifting. Building the evaluator early also paid off, because measuring retrieval exposed a bug that looked fine by eye. My fuller responsible-AI reflection is in `model_card.md`.

## Original PawPal+ features (still included)

- **Multi-pet task tracking**, **sorting by time**, **filtering** by pet and status.
- **Priority-based daily schedule** that skips what doesn't fit and explains why.
- **Conflict warnings** for every overlapping pair, never silently resolved.
- **Daily and weekly recurrence**: completing a task creates the next occurrence, with no duplicates.
- **Input validation**: durations must be positive and available time can't be negative.

See `pawpal_system.py` for the implementation.
