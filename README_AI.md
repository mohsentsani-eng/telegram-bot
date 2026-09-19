# Taranom Hamdeli — AI Assistant Edition

This version adds a **Gemini-powered educational analyst/assistant** without giving AI control over the bot's core educational logic.

## What Gemini does
- Analyze the student's existing educational profile.
- Analyze the latest assessment / learning / psychological results and stored Konkur guidance data.
- Answer general educational questions using the student's profile when useful.
- Save generated analyses in the local SQLite database.

## What Gemini does NOT do
- It does not calculate official scores.
- It does not select or modify questions.
- It does not change the question bank.
- It does not decide which test a student must take.
- It does not replace the counselor.

## Setup

1. Create a Gemini API key in Google AI Studio.
2. Copy `.env.example` to `.env`.
3. Set:

```env
GEMINI_API_KEY=YOUR_KEY_HERE
GEMINI_MODEL=gemini-3.8-flash
AI_ENABLED=true
```

Never commit the real `.env` or API key to GitHub.

The project uses Google's `google-genai` Python SDK. The model name is configurable through `GEMINI_MODEL`.

## New bot menu

**🤖 دستیار هوشمند**
- 📊 تحلیل پرونده من
- 📝 تحلیل آخرین نتیجه
- 💬 سؤال از دستیار

The existing exam/question-bank/database behavior remains separate from the AI module.

## AI Edition — expanded analysis

The AI layer now has five practical jobs:
- profile analysis
- latest-result analysis
- Konkur-result analysis
- combined analysis of educational/psychological/learning tests
- general educational Q&A personalized with the student's stored context

After completing an academic, psychological, or learning assessment, the bot offers an **AI analysis** button. After saving Konkur guidance, it offers a dedicated **Konkur analysis** button.

The AI never calculates official scores or controls question selection. It interprets data already calculated/stored by the bot.

The default model is `gemini-3.8-flash`, a current stable Gemini API model. It can be changed in `.env` with `GEMINI_MODEL`.


## انتخاب رشته ۱۴۰۴ با جست‌وجوی وب

در تحلیل «🎓 انتخاب رشته کنکور»، Gemini می‌تواند با Google Search grounding منابع عمومی وب را جست‌وجو کند و برای بخش رشته‌محل‌ها به دفترچه‌های ۱۴۰۴ سازمان سنجش و منابع تکمیلی مراجعه کند. این قابلیت با `AI_WEB_SEARCH=true` فعال است.

این بخش جایگزین سامانه رسمی سنجش یا انتخاب رشته رسمی نیست. خروجی فقط «رشته‌محل‌های قابل بررسی» را بر اساس اطلاعات کارنامه، سهمیه، بومی‌گزینی، علایق و منابع پیدا‌شده ارائه می‌کند و قبولی قطعی اعلام نمی‌کند. برای احتمال قبولی، داده تاریخی رتبه‌های قبولی باید با سال و منبع مشخص گزارش شود.
