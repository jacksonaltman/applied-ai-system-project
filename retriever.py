"""Keyword retriever over the markdown pet-care docs in knowledge/.

Each doc starts with `Title:`, `Species:`, `Stage:` and `Keywords:` header lines,
then a blank line, then the guidance body. Retrieval is deliberately simple and
deterministic: score each doc by species match, life-stage match, and keyword
overlap with the pet's profile, then return the top-k.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("pawpal.retriever")

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

# Scoring weights
SPECIES_MATCH = 5
GENERIC_DOC = 1
STAGE_MATCH = 3
KEYWORD_HIT = 2

_WORD = re.compile(r"[a-z]+")


@dataclass(frozen=True)
class Doc:
    id: str  # filename stem, e.g. "dog_adult"
    title: str
    species: str
    stage: str
    keywords: Tuple[str, ...]
    body: str


def life_stage(age_years: Optional[float]) -> Optional[str]:
    """Map an age to 'young' / 'adult' / 'senior'. Unknown age -> None."""
    if age_years is None:
        return None
    if age_years < 1:
        return "young"
    if age_years < 8:
        return "adult"
    return "senior"


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _parse(path: Path) -> Optional[Doc]:
    try:
        header, _, body = path.read_text(encoding="utf-8").partition("\n\n")
        fields = {}
        for line in header.splitlines():
            key, _, value = line.partition(":")
            fields[key.strip().lower()] = value.strip()
        return Doc(
            id=path.stem,
            title=fields["title"],
            species=fields["species"].lower(),
            stage=fields.get("stage", "all").lower(),
            keywords=tuple(k.strip().lower() for k in fields.get("keywords", "").split(",") if k.strip()),
            body=body.strip(),
        )
    except (OSError, KeyError, UnicodeDecodeError) as exc:  # malformed doc: skip, don't crash
        logger.warning("Skipping unreadable knowledge doc %s: %s", path.name, exc)
        return None


@lru_cache(maxsize=4)
def load_docs(directory: Path = KNOWLEDGE_DIR) -> Tuple[Doc, ...]:
    docs = [d for p in sorted(Path(directory).glob("*.md")) if (d := _parse(p))]
    logger.info("Loaded %d knowledge docs from %s", len(docs), directory)
    return tuple(docs)


def retrieve(
    species: str,
    breed: str = "",
    age_years: Optional[float] = None,
    extra_terms: str = "",
    k: int = 3,
    directory: Path = KNOWLEDGE_DIR,
) -> List[Doc]:
    """Return up to k docs most relevant to this pet, best first (score > 0 only)."""
    species = (species or "").strip().lower()
    stage = life_stage(age_years)
    profile_terms = _tokens(f"{species} {breed} {extra_terms}")

    scored: List[Tuple[int, Doc]] = []
    for doc in load_docs(directory):
        score = 0
        species_match = bool(species) and species == doc.species
        if species_match:
            score += SPECIES_MATCH
            if stage and doc.stage == stage:  # life stage only matters within the right species
                score += STAGE_MATCH
        elif doc.species == "any":
            score += GENERIC_DOC
        # Keywords may be multi-word ("guinea pig"); count a hit if all its words appear.
        score += KEYWORD_HIT * sum(1 for kw in doc.keywords if _tokens(kw) <= profile_terms)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda sd: (-sd[0], sd[1].id))  # ties broken by id: deterministic
    top = [d for _, d in scored[:k]]
    logger.info(
        "retrieve(species=%r, breed=%r, age=%r) -> %s",
        species, breed, age_years, [d.id for d in top],
    )
    return top
