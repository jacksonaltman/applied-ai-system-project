"""Evaluator for the AI pipeline. Run: python evaluate.py [--runs N]

1. Retrieval hit rate (offline, deterministic): for labeled pet profiles, is the
   expected doc in the retriever's top-k?
2. Schema pass rate (live, needs GEMINI_API_KEY): run the full agent N times per
   profile and report how many runs produced at least one valid suggestion, and
   what fraction of the model's individual suggestions passed validation.
"""
from __future__ import annotations

import argparse
import sys

import ai_agent
from pawpal_system import Pet
from retriever import retrieve

# (species, breed, age_years, doc id that MUST be retrieved)
RETRIEVAL_CASES = [
    ("dog", "labrador", 0.5, "dog_young"),
    ("dog", "poodle", 4, "dog_adult"),
    ("dog", "beagle", 11, "dog_senior"),
    ("cat", "tabby", 0.3, "cat_young"),
    ("cat", "persian", 5, "cat_adult"),
    ("cat", "siamese", 14, "cat_senior"),
    ("rabbit", "holland lop", 2, "rabbit"),
    ("small mammal", "guinea pig", 1, "small_mammal"),
    ("bird", "cockatiel", 3, "bird"),
    ("fish", "betta", 1, "fish"),
    ("reptile", "bearded dragon", 2, "reptile"),
    ("other", "axolotl", 2, "general"),  # unknown species should still get the generic guide
]


def eval_retrieval(k: int = 3) -> float:
    hits = 0
    print(f"Retrieval hit rate (top-{k})")
    for species, breed, age, expected in RETRIEVAL_CASES:
        got = [d.id for d in retrieve(species, breed, age, k=k)]
        ok = expected in got
        hits += ok
        print(f"  {'PASS' if ok else 'FAIL'}  {species}/{breed}/{age}y -> expected {expected}, got {got}")
    rate = hits / len(RETRIEVAL_CASES)
    print(f"  => {hits}/{len(RETRIEVAL_CASES)} = {rate:.0%}\n")
    return rate


def eval_schema(runs: int) -> None:
    print(f"Schema pass rate (live model, {runs} run(s) per profile)")
    if not ai_agent.is_configured():
        print("  SKIPPED: set GEMINI_API_KEY to run this part.\n")
        return
    ok_runs = total_valid = total_rejected = 0
    n = 0
    for species, breed, age, _ in RETRIEVAL_CASES[:6]:  # dog/cat life stages keep cost small
        for _ in range(runs):
            n += 1
            res = ai_agent.suggest_tasks(Pet("Eval", breed, species=species, age_years=age))
            ok_runs += res.error is None and bool(res.suggestions)
            total_valid += len(res.suggestions)
            total_rejected += res.rejected
    items = total_valid + total_rejected
    print(f"  runs with valid output: {ok_runs}/{n} = {ok_runs / n:.0%}")
    if items:
        print(f"  individual suggestions valid: {total_valid}/{items} = {total_valid / items:.0%}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3, help="live runs per profile")
    args = parser.parse_args()
    ai_agent.setup_logging()
    rate = eval_retrieval()
    eval_schema(args.runs)
    sys.exit(0 if rate == 1.0 else 1)
