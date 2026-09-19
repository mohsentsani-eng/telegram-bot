"""
Taranom Hamdeli - Quick Assessment / Channel Engagement Funnel
Channel: https://t.me/tarnoomhamdeli
"""

CHANNEL_URL = "https://t.me/tarnoomhamdeli"
CHANNEL_USERNAME = "@tarnoomhamdeli"

QUESTIONS = [
    ("grade", "🎓 پایه تحصیلی‌ات کدام است؟"),
    ("weak_subject", "📚 بیشتر در کدام درس احساس ضعف می‌کنی؟"),
    ("study_hours", "⏱️ به‌طور میانگین روزی چند ساعت مطالعه مفید داری؟"),
    ("problem", "🎯 بزرگ‌ترین مشکل تو در مطالعه چیست؟"),
    ("test_behavior", "📝 وقتی تست می‌زنی، بیشتر کدام حالت برایت پیش می‌آید؟"),
    ("goal", "🚀 مهم‌ترین هدفت برای امسال چیست؟"),
]

def start_text():
    return (
        "🎯 <b>ارزیابی سریع من</b>\n\n"
        "فقط به چند سؤال کوتاه جواب بده. کمتر از ۲ دقیقه زمان می‌برد "
        "و در پایان یک تحلیل اولیه متناسب با پاسخ‌هایت دریافت می‌کنی."
    )

def invitation_text():
    return (
        "🌱 <b>یک پیشنهاد برای ادامه مسیرت</b>\n\n"
        "اگر دوست داری نکات آموزشی، مطالب مشاوره‌ای، آزمون‌ها و "
        "محتوای کاربردی ترنم همدلی را دریافت کنی، "
        "می‌توانی عضو کانال مرکز شوی.\n\n"
        "📢 بعد از عضویت، روی «✅ عضو شدم» بزن."
    )

def keyboard():
    return [
        [{"text": "📢 عضویت در کانال", "url": CHANNEL_URL}],
        [{"text": "✅ عضو شدم", "callback_data": "check_center_channel"}],
    ]

def questions_count():
    return len(QUESTIONS)
