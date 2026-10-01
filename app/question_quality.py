"""Quality gates for the educational question bank.

These checks are deliberately conservative: they reject structural defects and
obvious low-quality options, but they do not pretend that a simple heuristic
can prove a question is pedagogically correct. Content review remains a
separate step.
"""

import re

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹")


def normalize_text(value):
    s = str(value or "").strip().translate(_ARABIC_DIGITS)
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = re.sub(r"\s+", " ", s)
    return s


def _compact(value):
    return re.sub(r"[^\w\dآ-ی]+", "", normalize_text(value)).lower()


def quality_issues(q):
    """Return human-readable structural quality issues.

    The function intentionally does not use an LLM or external service.
    """
    issues = []
    question = normalize_text(q.get("question"))
    options = [normalize_text(q.get(f"option_{x}")) for x in "abcd"]
    correct = normalize_text(q.get("correct_option")).upper()

    if not question:
        issues.append("empty_question")
    if any(not x for x in options):
        issues.append("empty_option")
    compact_options = [_compact(x) for x in options]
    if len(set(compact_options)) != 4:
        issues.append("duplicate_options")
    if correct not in {"A", "B", "C", "D"}:
        issues.append("invalid_correct_option")

    # Do not accept an option that is literally the question or a huge copy
    # of it; this catches malformed imports without judging legitimate prose.
    cq = _compact(question)
    for i, option in enumerate(compact_options):
        if option and (option == cq or (len(option) > 24 and option in cq)):
            issues.append(f"option_{'ABCD'[i]}_copies_question")

    # Four-option MCQs should not contain boilerplate "none/all" variants
    # mixed with ordinary answers unless the question explicitly asks for it.
    boilerplate = {"همه موارد", "همه موارد بالا", "هیچکدام", "هیچ کدام"}
    normalized_boilerplate = {normalize_text(x) for x in options}
    if normalized_boilerplate & boilerplate and not any(
        token in question for token in ("همه موارد", "هیچکدام", "هیچ کدام")
    ):
        issues.append("boilerplate_option_without_prompt")

    return sorted(set(issues))


def is_quality_ok(q):
    return not quality_issues(q)
