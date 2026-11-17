# PetCarePro Model Card

**System:** RAG task-suggestion feature in PetCarePro (extends my Module 2 project, PawPal+).
**Runtime model:** Google Gemini (`gemini-3.8-flash` by default, set with `GEMINI_MODEL`), called through the `google-genai` SDK.
**Retrieval:** keyword matching over 12 hand-written care guides in `knowledge/`.
**Built with:** Claude Code (Claude Sonnet 5.5) as my coding assistant.

## Intended use

Help a pet owner draft a daily care routine for a dog, cat, rabbit, small mammal, bird, fish or reptile. The output is a *draft*: every suggestion is shown to the owner for approval and nothing is saved automatically. It is **not** veterinary advice and is not meant for diagnosing, medicating or treating an animal.

## Reliability evidence

All numbers below are from real runs. They can be regenerated with `python -m pytest -v` and `python evaluate.py` (which writes [evaluation_results.md](evaluation_results.md)).

### Summary

| check | how it is measured | result |
|---|---|---|
| Scheduler unit tests | `tests/test_pawpal.py` | 22 / 22 pass |
| AI-layer unit tests (model call faked, no network) | `tests/test_ai.py` | 14 / 14 pass |
| Retrieval hit rate (top-3) | `evaluate.py`, 12 labeled pet profiles | 12 / 12 = 100% |
| Guardrail rejection of bad model output | `test_parse_rejects_bad_items_but_keeps_good_ones` | 5 of 5 bad items rejected, 1 good item kept |
| Schema pass rate on live Gemini output | `python evaluate.py --runs 3` | **not yet run** (needs `GEMINI_API_KEY`; see the "Surprises" section for why the hit rate alone is not enough) |

### AI-layer test log (`pytest -v`)

| test | what it proves | result |
|---|---|---|
| test_life_stage_boundaries | age maps to young / adult / senior | PASS |
| test_retrieves_species_and_stage_match_first | puppy gets `dog_young`, 12-year-old cat gets `cat_senior` | PASS |
| test_unknown_species_falls_back_to_general_doc | unknown species gets only the general guide | PASS |
| test_retrieval_is_deterministic | same profile, same guides, every time | PASS |
| test_parse_accepts_valid_output | well-formed JSON becomes typed suggestions | PASS |
| test_parse_rejects_bad_items_but_keeps_good_ones | bad time, bad duration, ungrounded source, bad enum, duplicate are dropped | PASS |
| test_parse_skips_tasks_the_pet_already_has | no duplicate of an existing task | PASS |
| test_parse_raises_on_non_json | non-JSON output is detected | PASS |
| test_suggest_tasks_happy_path_and_to_task | suggestion converts to a real `Task` | PASS |
| test_suggest_tasks_retries_once_on_bad_output | one retry, then success | PASS |
| test_suggest_tasks_reports_error_when_output_never_valid | gives up with an error message | PASS |
| test_suggest_tasks_never_raises_on_api_failure | network error does not crash the app | PASS |
| test_prompt_contains_retrieved_docs_and_profile | retrieved text actually reaches the model prompt | PASS |
| test_feature_disabled_without_api_key | no key means feature off, no crash | PASS |

### Retrieval evaluation (from `evaluation_results.md`)

| species | breed | age_years | expected | retrieved | result |
|---|---|---|---|---|---|
| dog | labrador | 0.5 | dog_young | dog_young, dog_adult, dog_senior | PASS |
| dog | poodle | 4 | dog_adult | dog_adult, dog_senior, dog_young | PASS |
| dog | beagle | 11 | dog_senior | dog_senior, dog_adult, dog_young | PASS |
| cat | tabby | 0.3 | cat_young | cat_young, cat_adult, cat_senior | PASS |
| cat | persian | 5 | cat_adult | cat_adult, cat_senior, cat_young | PASS |
| cat | siamese | 14 | cat_senior | cat_senior, cat_adult, cat_young | PASS |
| rabbit | holland lop | 2 | rabbit | rabbit, general | PASS |
| small mammal | guinea pig | 1 | small_mammal | small_mammal, general | PASS |
| bird | cockatiel | 3 | bird | bird, general | PASS |
| fish | betta | 1 | fish | fish, general | PASS |
| reptile | bearded dragon | 2 | reptile | reptile, general | PASS |
| other | axolotl | 2 | general | general | PASS |

## Limitations and biases

- **Coverage bias.** The knowledge base has 12 short guides, and 6 of them are for dogs and cats. Every other species gets a single guide for all ages and breeds. An owner of a rabbit, bird or reptile gets less specific advice than an owner of a dog.
- **One-size life stages.** "Senior" starts at 8 years for every species. That is wrong for many animals: a giant-breed dog is senior much earlier, and a parrot or tortoise much later. Species that have only one guide ignore age entirely.
- **Breed is mostly ignored.** Breed only matters when it matches a keyword in a guide, so a brachycephalic dog or a hypoallergenic-coat breed isn't handled differently.
- **Keyword retrieval is brittle.** It does not understand synonyms or misspellings ("pup", "kitty", "labradore"). A misspelled species falls back to the general guide.
- **The guides are my own summaries, not veterinary sources.** The advice is generic and its quantities (meal counts, walk lengths) are rules of thumb. The model can only be as good as these guides.
- **Validation checks form, not truth.** The guardrails verify that output is well-formed and grounded in a retrieved guide. They cannot tell whether the model *misread* a guide or suggested a time that is a poor fit for the animal. The human reviewer is the real check on quality.
- **Scheduling assumptions.** Suggested start times are generic (for example, morning and evening) and ignore the owner's actual availability. Tasks that span midnight are untested.
- **Language and access.** English only, and a Gemini API key is required for the AI feature.
- **Privacy.** Pet name, species, breed and existing task names are sent to Google's Gemini API as part of the prompt. Owner name is not sent, but users should not put personal information into pet or task names.

## Potential misuse and mitigations

| risk | how it could happen | mitigation in place | still to do |
|---|---|---|---|
| Treating the output as veterinary advice | An owner relies on a suggested routine for a sick or special-needs animal | The feature is described as a draft; the owner must approve each task; guides contain care routines, not diagnosis or dosing; the UI states "not veterinary advice" above the suggestions | Make the notice more prominent (for example, require acknowledgement) |
| Prompt injection through free-text fields | Someone types instructions into the breed or pet name field that end up in the prompt | Output must match a strict JSON schema, every task must cite a guide that was actually retrieved, and nothing is saved without human approval | Sanitize and length-limit free-text fields before they enter the prompt |
| Harmful or absurd tasks | The model returns an unsafe or off-topic task | Source-grounding check, duration and time validation, and human review | Add a keyword blocklist for medication and dosing language |
| Cost or abuse of the API key | Repeated clicks or runaway evaluation runs | Retries are limited to one, suggestion count is capped at 8, and the key is read from an environment variable, never hardcoded or committed (`.env` is git-ignored) | Add a per-session rate limit |
| Data exposure | Logs may contain pet names and model output | Logs stay local (`pawpal.log` is git-ignored) | Add log redaction if the app is ever deployed for other users |

## What surprised me while testing reliability

1. **A 100% hit rate hid a real bug.** My retrieval evaluator passed 12/12 even while the retriever was returning guides for the wrong species: a rabbit's top-3 included `cat_adult` and `dog_adult`, because the life-stage bonus was applied to any species. The metric only asked "is the *expected* guide in the top 3", so it couldn't see the junk around it. I noticed it only because I read the printed results line by line. I fixed the scoring so the life-stage bonus applies only to the matching species, and I now know that a pass rate needs a second metric (for example, "no wrong-species guides") to be trustworthy.
2. **The first live call failed for a reason my tests could not catch.** The default model ID `gemini-2.5-flash` had been retired for new users and returned `404 NOT_FOUND`. All 36 tests passed because the model call is faked. This taught me that offline tests prove my logic, but only a live run proves the integration. It also made me stop swallowing the API's error text: the UI now shows the reason, and the model ID is configurable.
3. **Most failures were boring.** I expected the interesting risk to be the model hallucinating. In practice the bugs were in my own code and configuration (scoring logic, a stale model name).

## Collaboration with AI

I used Claude Code as a pair-programmer for design, implementation, tests and docs, and Gemini as the runtime model inside the app. I reviewed and ran what Claude Code produced, and made the product decisions.

**One suggestion I accepted: RAG with simple keyword matching.** Claude Code recommended Retrieval-Augmented Generation over the other options (agentic workflow, fine-tuning, a testing-only feature). The argument was that a pet-care knowledge base feeds directly into the existing `Task` and `Scheduler` classes, so the AI output changes real behavior rather than sitting beside it. I agreed, and when it proposed starting with keyword matching instead of embeddings, I accepted that too. It keeps the project dependency-light and every retrieval result is easy to explain and test.

**One suggestion I did not accept as written: the default model and the no-key behavior.** Claude Code's plan assumed the Claude API with a small, cheap model as the default. I did not use that, because I already had a Gemini API key, so I told it to use Gemini instead and the code was rewritten around the `google-genai` SDK. In the same round it also proposed an offline fallback that would generate tasks straight from the retrieved guides when no key is set, and an evaluator with three metrics (including a consistency check). I scoped those down: with no key, the AI feature is simply disabled, and the evaluator measures retrieval hit rate and schema pass rate only. This keeps the code smaller and easier to read, at the cost of the AI path not being demoable without a key.

**Where the AI was wrong.** Claude Code picked a default Gemini model ID that was already retired, which caused the 404 described above, and it initially misreported that my `diagrams/` folder was empty when it already held my UML files. Both were caught by checking real output (the log file and `git status`) instead of trusting the summary.
