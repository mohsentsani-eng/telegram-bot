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


CROSS_DOMAIN = {
    "ریاضی": {"قلب","ریه","معده","سلول","فتوسنتز","خلیج فارس","جنگ جهانی"},
    "ریاضی و آمار": {"قلب","ریه","فتوسنتز","جنگ جهانی","آرایه ادبی"},
    "هندسه": {"قلب","ریه","فتوسنتز","جنگ جهانی","آرایه ادبی"},
    "فیزیک": {"قلب","ریه","فتوسنتز","آرایه ادبی","مترادف","مفعول"},
    "شیمی": {"قلب","ریه","مترادف","مفعول","آرایه ادبی","جنگ جهانی"},
    "زیست‌شناسی": {"مترادف","مفعول","آرایه ادبی","قافیه","معادله درجه دوم"},
    "علوم": {"مترادف","مفعول","آرایه ادبی","قافیه","جنگ جهانی"},
    "فارسی": {"نیوتن","وات","پاسکال","فتوسنتز","الکترون","قاره آفریقا"},
    "نگارش": {"نیوتن","وات","پاسکال","فتوسنتز","الکترون"},
    "تاریخ": {"نیوتن","فتوسنتز","آرایه ادبی","قافیه"},
    "جغرافیا": {"مترادف","مفعول","فتوسنتز","نیوتن"},
    "جامعه‌شناسی": {"نیوتن","فتوسنتز","قافیه","مفعول"},
    "دین و زندگی": {"نیوتن","فتوسنتز","آرایه ادبی","قاره آفریقا"},
    "عربی": {"نیوتن","فتوسنتز","سلول","قاره آفریقا"},
    "زبان انگلیسی": {"نیوتن","فتوسنتز","آرایه ادبی"},
}


def _cross_domain_issue(subject, options):
    terms = CROSS_DOMAIN.get(normalize_text(subject), set())
    if not terms:
        return False
    joined = " ".join(options)
    return any(term in joined for term in terms)


def quality_issues(q):
    """Return human-readable structural quality issues.

    The function intentionally does not use an LLM or external service.
    """
    issues = []
    question = normalize_text(q.get("question"))
    subject = normalize_text(q.get("subject"))
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

    if _cross_domain_issue(subject, options):
        issues.append("obvious_cross_domain_option")

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
