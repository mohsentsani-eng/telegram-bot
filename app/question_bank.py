"""Reliable question-bank bootstrap.

This module makes the bundled educational bank self-healing:
1) always loads the repository's bundled CSV banks (idempotently),
2) guarantees at least 10 unique playable questions for every existing
   grade/track/subject/chapter/topic/difficulty bucket,
3) never deletes or overwrites student records or imported questions.

The generated variants are a temporary technical floor so the bot never
gets stuck because a bucket has only 6 questions. They are clearly marked
as generated variants and are not presented as official textbook questions.
The long-term bank can replace them with professionally authored,
chapter-specific questions through the admin CSV import.
"""

from collections import defaultdict
import csv
from pathlib import Path

from . import db

ROOT = Path(__file__).resolve().parent.parent
SEED_FILES = (
    ROOT / "data" / "expanded_questions.csv",
    ROOT / "data" / "d10_humanities_questions.csv",
    ROOT / "data" / "seed_questions.csv",
)

MINIMUM = 10


def _seed_bundled():
    inserted = 0
    for path in SEED_FILES:
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    try:
                        if db.insert_question_if_new(row):
                            inserted += 1
                    except Exception as exc:
                        print(f"[QUESTION-BANK] skipped invalid row in {path.name}: {exc}", flush=True)
        except Exception as exc:
            print(f"[QUESTION-BANK] seed file failed: {path.name}: {exc}", flush=True)
    return inserted


def _rotate_options(row, shift):
    opts = [row["option_a"], row["option_b"], row["option_c"], row["option_d"]]
    correct = row["correct_option"]
    idx = {"A": 0, "B": 1, "C": 2, "D": 3}[correct]
    shift = shift % 4
    rotated = opts[shift:] + opts[:shift]
    new_correct = "ABCD"[(idx - shift) % 4]
    return rotated, new_correct


def _make_variant(row, n):
    opts, correct = _rotate_options(row, n)
    prefixes = {
        1: "صورت تمرینی ۱: ",
        2: "صورت تمرینی ۲: ",
        3: "صورت تمرینی ۳: ",
        4: "صورت تمرینی ۴: ",
        5: "صورت تمرینی ۵: ",
        6: "صورت تمرینی ۶: ",
    }
    q = dict(row)
    q["question"] = prefixes.get(n, f"صورت تمرینی {n}: ") + str(row["question"]).strip()
    q["option_a"], q["option_b"], q["option_c"], q["option_d"] = opts
    q["correct_option"] = correct
    q["source"] = "ترنم همدلی – بازتولید تمرینی"
    q["source_type"] = "generated_variant"
    q["source_year"] = "1405"
    q["explanation"] = (
        str(row["explanation"] or "").strip()
        + (" " if str(row["explanation"] or "").strip() else "")
        + "این سؤال نسخه تمرینی بازنویسی‌شده از همان مفهوم است."
    )
    return q


def ensure_minimum_questions(minimum=MINIMUM):
    """Top up every existing curriculum bucket to the minimum playable size."""
    rows = [dict(r) for r in db.list_questions({})]
    groups = defaultdict(list)

    # Difficulty is intentionally part of the bucket because the bot filters
    # by it for regular tests. «تشخیصی» can still use the complete topic bucket.
    keys = ("grade", "track", "subject", "book", "chapter", "topic", "difficulty")
    for row in rows:
        groups[tuple(row.get(k, "") or "" for k in keys)].append(row)

    inserted = 0
    for key, bucket in groups.items():
        if len(bucket) >= minimum:
            continue
        needed = minimum - len(bucket)

        # Deterministic source selection + option rotation gives unique records
        # without inventing a new factual answer.
        for n in range(1, needed + 1):
            source = bucket[(n - 1) % len(bucket)]
            variant = _make_variant(source, n)
            try:
                if db.insert_question_if_new(variant):
                    inserted += 1
            except Exception as exc:
                print(
                    f"[QUESTION-BANK] variant failed for "
                    f"{key[0]} / {key[1]} / {key[2]}: {exc}",
                    flush=True,
                )
    return inserted


def bootstrap_question_bank():
    seeded = _seed_bundled()
    variants = ensure_minimum_questions()
    total = db.count_questions({})
    print(
        f"[QUESTION-BANK] ready: total={total}, bundled_added={seeded}, "
        f"generated_variants={variants}, minimum={MINIMUM}",
        flush=True,
    )
    return {"total": total, "seeded": seeded, "variants": variants}
