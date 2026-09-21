import os
import json
import asyncio
from typing import Optional

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None


def clean_ai_text(text: str) -> str:
    """Clean Telegram-facing AI output and block leaked internal instructions."""
    import re
    text = text or ""

    # Remove HTML/Markdown formatting that should not appear raw.
    text = re.sub(r"</?(?:b|strong|i|em|u|s|code|pre)>", "", text, flags=re.I)
    text = text.replace("**", "").replace("__", "")

    # Remove common leaked internal/meta lines.
    patterns = [
        r"(?im)^\s*\*?\s*Taranom Hamdeli Assistant\?.*$",
        r"(?im)^\s*\*?\s*No guessing/external info\?.*$",
        r"(?im)^\s*\*?\s*No absolute promises or clinical labels\?.*$",
        r"(?im)^\s*\*?\s*CONTEXT\s*:?.*$",
        r"(?im)^\s*\*?\s*REQUEST\s*:?.*$",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

SYSTEM_PROMPT = """
تو «دستیار هوشمند آموزشی ترنم همدلی» هستی.
وظیفه تو تحلیل و کمک آموزشی شخصی‌سازی‌شده است؛ نه محاسبه رسمی نمره، نه تصمیم‌گیری قطعی به جای دانش‌آموز یا مشاور.
فقط بر اساس داده‌های ارائه‌شده صحبت کن و اگر داده‌ای وجود ندارد، آن را حدس نزن.
نتیجه آزمون‌ها را تفسیر کن، الگوها را توضیح بده، نقاط قوت و حوزه‌های نیازمند توجه را مشخص کن و اقدامات عملی پیشنهاد بده.
در تحلیل کنکور، رتبه/تراز/معدل را فقط تفسیر کن و درباره قبولی یا آینده وعده قطعی نده.
در تحلیل شخصیت و آزمون‌های روان‌شناختی، از برچسب قطعی و تشخیص بالینی خودداری کن و نتیجه را به‌عنوان «نشانه/الگو در داده آزمون» بیان کن.
پاسخ فارسی، روشن، محترمانه و کاربردی باشد.
"""


def enabled() -> bool:
    return bool(
        os.getenv("AI_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        and os.getenv("GEMINI_API_KEY", "").strip()
    )


def _client():
    if not enabled() or genai is None:
        return None
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY", "").strip())


def _model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"


def _models_to_try() -> list[str]:
    # Only use model IDs that are currently documented as available.
    primary = _model()
    raw = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash-lite,gemini-2.5-flash")
    result = [primary]
    for name in raw.split(","):
        name = name.strip()
        if name and name not in result:
            result.append(name)
    return result


def _compact(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str, separators=(",", ":"))


class GeminiQuotaExhausted(RuntimeError):
    """Gemini API quota/rate-limit is exhausted; retrying every model is not useful."""


class GeminiIncompleteResponse(RuntimeError):
    """Gemini stopped because the configured output token limit was reached."""


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).upper()
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "QUOTA_EXCEEDED" in msg


def local_konkur_fallback(student, snapshot) -> str:
    """Deterministic report used when Gemini quota is unavailable. Never invents رشته‌محل data."""
    import json as _json
    rows = snapshot.get("guidance", []) or []
    payload = {}
    for row in rows:
        if row.get("guidance_type") == "konkur":
            try:
                payload = _json.loads(row.get("payload_json") or "{}")
            except Exception:
                payload = {}
            break
    labels = [
        ("group", "گروه آزمایشی"), ("year", "سال کارنامه"), ("gender", "جنسیت"),
        ("diploma", "نوع دیپلم"), ("quota", "سهمیه نهایی"), ("rank_quota", "رتبه در سهمیه"),
        ("last_eligible_rank", "آخرین رتبه مجاز"), ("rank_country", "رتبه کشوری"),
        ("exam_score", "نمره کل آزمون اختصاصی"), ("academic_score", "نمره کل سابقه تحصیلی"),
        ("final_score", "نمره کل نهایی"), ("final_gpa", "معدل"),
        ("study_province", "استان محل تحصیل"), ("birth_province", "استان محل تولد"),
        ("native_province", "استان بومی"), ("native_area", "ناحیه بومی"),
        ("native_pole", "قطب بومی"), ("eligibility", "وضعیت مجاز بودن"),
        ("cities", "شهرهای مورد علاقه"), ("interests", "رشته‌های مورد علاقه"),
        ("university_types", "دوره/دانشگاه‌های قابل قبول"),
    ]
    lines=["⚠️ تحلیل هوشمند موقت به دلیل اتمام سهمیه Gemini انجام نشد؛ اما اطلاعات کارنامه شما از بین نرفته است.", "", "📋 خلاصه اطلاعات ثبت‌شده:"]
    for key, label in labels:
        value = str(payload.get(key, "")).strip()
        if value:
            lines.append(f"• {label}: {value}")
    lines += ["", "🎯 وضعیت فعلی:",
              "• داده‌های لازم برای تحلیل انتخاب رشته در پرونده ذخیره شده است.",
              "• بدون دسترسی به Gemini و داده زنده دفترچه، کدرشته‌محل یا شانس قبولی حدس زده نمی‌شود.",
              "• پس از رفع سهمیه API، همین پرونده قابل تحلیل مجدد است.",
              "", "🔧 اقدام لازم: در Google AI Studio / پروژه متصل به API، سهمیه و وضعیت Billing را بررسی کنید."]
    return "\n".join(lines)


def build_context(student, snapshot) -> str:
    profile = {
        "نام": f"{student['first_name']} {student['last_name']}",
        "پایه": student["grade"],
        "رشته": student["track"] or "",
        "سوابق_آزمون": [dict(x) for x in snapshot.get("assessments", [])[:30]],
        "تسلط_مباحث": [dict(x) for x in snapshot.get("mastery", [])[:50]],
        "نتایج_روانشناختی": [dict(x) for x in snapshot.get("psych", [])[:50]],
        "مهارت_یادگیری": [dict(x) for x in snapshot.get("learning", [])[:50]],
        "نتایج_کنکور_و_راهنمایی": [dict(x) for x in snapshot.get("guidance", [])[:30]],
        "درخواست_مشاوره": [dict(x) for x in snapshot.get("requests", [])[:10]],
        "گفتگوهای_اخیر_با_AI": [dict(x) for x in snapshot.get("ai_history", [])[:8]],
    }
    return _compact(profile)


async def _one_request(client, model_name: str, full: str, max_tokens: int, use_web_search: bool = False) -> str:
    # For ordinary educational analysis we keep the request local to the supplied
    # student record. For Konkur 1404 analysis, optional Google Search grounding
    # lets Gemini verify the official Sanjesh booklet and current/public sources.
    config_kwargs = dict(
        temperature=0.35,
        max_output_tokens=max_tokens,
    )
    if use_web_search and types is not None and os.getenv("AI_WEB_SEARCH", "true").strip().lower() in {"1", "true", "yes", "on"}:
        config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    config = types.GenerateContentConfig(**config_kwargs)
    # Hard timeout prevents the Telegram handler from appearing stuck forever.
    response = await asyncio.wait_for(
        client.aio.models.generate_content(
            model=model_name,
            contents=full,
            config=config,
        ),
        timeout=float(os.getenv("GEMINI_REQUEST_TIMEOUT", "90")),
    )
    # Do not silently send truncated answers to Telegram. Gemini reports
    # MAX_TOKENS when the output limit is reached; the caller can retry with
    # a larger budget instead of displaying an incomplete report.
    try:
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            finish_reason = getattr(candidates[0], "finish_reason", None)
            finish_text = str(finish_reason or "").upper()
            if "MAX_TOKENS" in finish_text or "MAXTOKENS" in finish_text:
                raise GeminiIncompleteResponse("Gemini response reached max_output_tokens")
    except GeminiIncompleteResponse:
        raise
    except Exception:
        pass
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return clean_ai_text(text.strip())


async def ask(prompt: str, context: Optional[str] = None, max_tokens: int = 1800, use_web_search: bool = False) -> str:
    client = _client()
    if client is None:
        raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY and AI_ENABLED=true in .env")

    full = SYSTEM_PROMPT + "\n\nCONTEXT:\n" + (context or "اطلاعات پرونده در دسترس نیست.") + "\n\nREQUEST:\n" + prompt
    last_error = None

    try:
        for model_name in _models_to_try():
            # Two attempts per model: enough to absorb a transient 503 without
            # making the Telegram user wait through a long chain of retries.
            for attempt in range(1, 3):
                print(f"[AI] requesting {model_name} (attempt {attempt}/2)", flush=True)
                try:
                    text = await _one_request(client, model_name, full, max_tokens, use_web_search)
                    print(f"[AI] success: {model_name}", flush=True)
                    return text
                except asyncio.TimeoutError as e:
                    last_error = e
                    print(f"[AI] timeout: {model_name} (attempt {attempt}/2)", flush=True)
                except GeminiIncompleteResponse as e:
                    last_error = e
                    print(f"[AI] incomplete response from {model_name}; increasing output budget", flush=True)
                    # The first request may simply have hit the output ceiling.
                    # Retry the same model with a larger budget before falling back.
                    if attempt == 1:
                        retry_tokens = min(max(int(max_tokens * 2), 2800), 6000)
                        try:
                            text = await _one_request(client, model_name, full, retry_tokens, use_web_search)
                            print(f"[AI] success after token-budget retry: {model_name}", flush=True)
                            return text
                        except GeminiIncompleteResponse as retry_error:
                            last_error = retry_error
                        except Exception as retry_error:
                            last_error = retry_error
                            print(f"[AI] token-budget retry error {model_name}: {type(retry_error).__name__}: {str(retry_error)[:240]}", flush=True)
                except Exception as e:
                    last_error = e
                    msg = str(e).upper()
                    print(f"[AI] error {model_name}: {type(e).__name__}: {str(e)[:240]}", flush=True)
                    # A quota exhaustion is project-level/model-quota related; repeating
                    # the same request or immediately switching models can waste quota.
                    if _is_quota_error(e):
                        raise GeminiQuotaExhausted(str(e)) from e
                    transient = any(code in msg for code in (
                        "503", "UNAVAILABLE", "500", "502", "504", "INTERNAL", "TIMEOUT"
                    ))
                    if not transient:
                        continue

                if attempt == 1:
                    await asyncio.sleep(2.0)

        # If Google Search grounding is the part that failed (for example due to
        # project billing/tool availability), make one final non-grounded attempt.
        # This keeps the Telegram bot usable; the prompt explicitly forbids
        # inventing رشته‌محل data when search is unavailable.
        if use_web_search:
            print("[AI] Google Search grounding failed; retrying without web search", flush=True)
            try:
                for model_name in _models_to_try():
                    try:
                        text = await _one_request(client, model_name, full, max_tokens, False)
                        return text + "\n\n⚠️ توجه: جست‌وجوی وب در این نوبت در دسترس نبود؛ بنابراین اطلاعات رشته‌محل/منابعی که نیاز به بررسی زنده دارند قطعی فرض نشده‌اند."
                    except Exception as e:
                        last_error = e
                        print(f"[AI] fallback error {model_name}: {type(e).__name__}: {str(e)[:180]}", flush=True)
            except Exception as e:
                last_error = e

        detail = str(last_error)[:500] if last_error else "unknown error"
        raise RuntimeError(
            "سرویس Gemini پاسخ نداد. جزئیات فنی: " + detail
        ) from last_error
    finally:
        try:
            client.close()
        except Exception:
            pass


async def analyze_profile(student, snapshot) -> str:
    return await ask("""
یک تحلیل جامع از پرونده این دانش‌آموز تهیه کن.
ساختار:
1. تصویر کلی وضعیت فعلی
2. نقاط قوت قابل مشاهده
3. حوزه‌های نیازمند توجه
4. الگوهای مهم در روند نتایج
5. تفسیر آزمون‌های روان‌شناختی و مهارت‌های یادگیری، فقط در حد داده‌های موجود
6. سه اقدام عملی برای 7 روز آینده
7. نکته‌ای که مشاور در جلسه بعد بررسی کند
اگر داده کافی برای بخشی وجود ندارد، همان بخش را «داده کافی نداریم» اعلام کن.
""", build_context(student, snapshot))


async def analyze_latest_result(student, snapshot) -> str:
    return await ask("""
آخرین نتیجه یا نتایج ثبت‌شده این دانش‌آموز را تحلیل کن.
روی معنی آموزشی داده‌ها تمرکز کن: چه چیزی خوب است، چه چیزی نیازمند توجه است، آیا روندی نسبت به نتایج قبلی دیده می‌شود و قدم بعدی چیست.
اگر نتیجه کنکور موجود است، رتبه، رتبه در سهمیه، تراز/نمره و سوابق تحصیلی را جداگانه تفسیر کن و از پیش‌بینی قبولی خودداری کن.
در پایان یک برنامه کوتاه اقدام ارائه بده.
""", build_context(student, snapshot))


async def analyze_assessment(student, snapshot, assessment_id: int) -> str:
    return await ask(f"""
آزمون با شناسه داخلی {assessment_id} را از میان سوابق پیدا کن و همان آزمون را محور تحلیل قرار بده.
اگر شناسه یا داده آزمون در Context وجود ندارد، صادقانه اعلام کن.
تحلیل شامل این موارد باشد:
- نتیجه کلی
- نقاط قوت
- مباحث/حوزه‌های ضعیف‌تر
- الگوی خطا یا تسلط، اگر داده موجود است
- معنی آموزشی نتیجه
- 3 اقدام بعدی
- پیشنهاد برای آزمون یا مرور بعدی
""", build_context(student, snapshot))


async def analyze_konkur(student, snapshot) -> str:
    return await ask("""
تو مسئول تحلیل آموزشی و انتخاب رشته بر اساس کارنامه ۱۴۰۴ هستی.
اول اطلاعات ثبت‌شده را کامل بررسی کن و اگر فیلدی ناقص است دقیقاً نام همان فیلد را بگو.

مبنای تحلیل:
- کارنامه ملاک انتخاب رشته ۱۴۰۴: نمره کل آزمون اختصاصی، نمره کل سابقه تحصیلی، نمره کل نهایی، رتبه در سهمیه، رتبه کشوری.
- وضعیت بومی: استان محل تحصیل سه سال آخر، استان تولد، استان بومی، ناحیه بومی و قطب بومی.
- سهمیه نهایی و وضعیت مجاز بودن دوره‌ها.
- رشته‌محل‌های دفترچه انتخاب رشته ۱۴۰۴ و ضوابط بومی‌گزینی/سهمیه‌ها.
- علایق رشته‌ای، شهر و نوع دانشگاه مورد قبول دانش‌آموز.

خروجی را دقیقاً با این ساختار بده:
1. 📋 خلاصه کامل کارنامه
2. 📊 تفسیر رتبه در سهمیه، رتبه کشوری، نمره کل نهایی، نمره کل آزمون اختصاصی و سابقه تحصیلی
3. 🗺️ تحلیل سهمیه و بومی‌گزینی
4. 🎯 رشته‌های هم‌راستا با علایق ثبت‌شده
5. 🏫 رشته‌محل‌های مشخص قابل بررسی (نه فقط نام رشته):
   - کدرشته‌محل، رشته، دانشگاه، شهر، دوره و ظرفیت را هرجا از دفترچه پیدا کردی ذکر کن
   - گزینه‌های مطابق‌تر با رتبه/سهمیه/علایق
   - گزینه‌های مرزی یا نیازمند داده قبولی تاریخی
   - مواردی که به دلیل شرط جنسیت/سهمیه/بومی/مجاز بودن باید کنار گذاشته شوند
6. 📍 شهرها و دانشگاه‌هایی که باید در دفترچه بررسی شوند
7. ⚠️ شرایط یا محدودیت‌های مهم هر گزینه، اگر در داده/دفترچه موجود باشد
8. 📝 پیشنهاد چینش انتخاب‌ها بر اساس «علاقه + امکان‌پذیری»، بدون ادعای قبولی قطعی
9. ❓ اطلاعاتی که هنوز برای تحلیل دقیق‌تر لازم است.

مهم:
- دفترچه مشخص می‌کند چه رشته‌محل‌هایی و چه شرایطی وجود دارند؛ برای برآورد شانس قبولی، باید داده رتبه‌های قبولی سال‌های قبل یا داده رسمی مشابه هم وجود داشته باشد. اگر چنین داده‌ای در Context نیست، وانمود نکن که شانس قبولی را دقیق می‌دانی.
- هیچ قبولی را قطعی اعلام نکن.
- هیچ اطلاعاتی خارج از داده‌های ارائه‌شده یا منابع مبنا نساز.
- اگر داده کافی نیست، واضح بگو چه چیزی کم است.
- حتماً برای بخش رشته‌محل‌ها جست‌وجوی وب انجام بده. اولویت با دفترچه‌ها و اطلاعیه‌های سازمان سنجش است؛ سپس منابع ثانویه معتبر فقط برای داده‌های تکمیلی. برای دفترچه اصلی، این مسیرهای رسمی را نیز در جست‌وجو هدف بگیر: www8.sanjesh.org/download/1404/sar/cs/riazi.pdf ، tajrobi.pdf ، Ensani.pdf ، honar.pdf ، zaban.pdf.
- در جست‌وجو از عبارت‌های دقیق شامل «کنکور سراسری ۱۴۰۴»، گروه آزمایشی، نام رشته، شهر/دانشگاه و «دفترچه انتخاب رشته» استفاده کن.
- اگر برای یک رشته‌محل کدرشته‌محل، نام دانشگاه، شهر، نوع دوره، ظرفیت یا شرط خاص را پیدا کردی، همان مورد را با منبع گزارش کن؛ اگر پیدا نکردی، حدس نزن.
- برای داده‌های رتبه قبولی سال‌های قبل، سال و منبع را دقیق ذکر کن و آن را «داده تاریخی/غیراسمی» معرفی کن مگر اینکه منبع رسمی باشد.
- خروجی را در پایان با بخشی به نام «🔎 منابع بررسی‌شده» تمام کن و حداکثر 8 منبع مهم را با عنوان و URL ساده فهرست کن.
""", build_context(student, snapshot), 2600, use_web_search=True)


async def analyze_tests(student, snapshot) -> str:
    return await ask("""
نتایج آزمون‌های تحصیلی، روان‌شناختی و مهارت‌های یادگیری را کنار هم تحلیل کن.
هدف، ساختن یک تصویر یکپارچه از وضعیت آموزشی دانش‌آموز است.
تناقض‌ها یا هم‌راستایی‌های بین نتایج را مشخص کن؛ اما اگر داده برای نتیجه‌گیری کافی نیست، حدس نزن.
در پایان بگو مشاور برای دقیق‌تر شدن تصویر چه اطلاعاتی را بهتر است در جلسه بعد جمع‌آوری کند.
""", build_context(student, snapshot))


async def general_help(student, snapshot, question: str) -> str:
    prompt = f"""
دانش‌آموز این سؤال را پرسیده است:
{question}

به سؤال پاسخ بده و در صورت وجود داده مرتبط از پرونده او استفاده کن.
اگر سؤال عمومی است، پاسخ عمومی اما کاربردی بده.
اگر برای پاسخ شخصی‌سازی‌شده اطلاعاتی لازم است، حداکثر 3 سؤال کوتاه تکمیلی بپرس.
"""
    return await ask(prompt, build_context(student, snapshot), 1600)


async def analyze_custom_data(student, snapshot, data_text: str) -> str:
    prompt = f"""
کاربر داده‌های زیر را برای تحلیل آموزشی ارسال کرده است:

--- داده ارسالی ---
{data_text}
--- پایان داده ارسالی ---

این داده را دقیق و بدون ساختن اطلاعات جدید تحلیل کن.
اگر داده مربوط به کنکور یا کارنامه است، اعداد و بخش‌های مختلف را جداگانه توضیح بده.
اگر مربوط به آزمون یا تست است، الگوهای مهم، نقاط قوت و حوزه‌های نیازمند توجه را استخراج کن.
اگر داده عمومی یا ترکیبی است، ابتدا نوع اطلاعات را مشخص کن و سپس تحلیل مناسب ارائه بده.

خروجی را با این ساختار تهیه کن:
1. برداشت کلی
2. مهم‌ترین نکات
3. نقاط قوت
4. حوزه‌های نیازمند توجه
5. اگر روند یا رابطه قابل مشاهده‌ای وجود دارد
6. سه اقدام عملی پیشنهادی
7. چه اطلاعاتی برای تحلیل دقیق‌تر لازم است

از پیش‌بینی قطعی، تشخیص روان‌شناختی/پزشکی، یا نتیجه‌گیری فراتر از داده‌ها خودداری کن.
"""
    return await ask(prompt, build_context(student, snapshot), 2000)
