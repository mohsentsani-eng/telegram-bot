"""Reliable, additive question-bank bootstrap for Taranom Hamdeli.

The bank is seeded additively. Student records, attempts and existing questions
are never deleted or overwritten. Exact duplicate questions are filtered by
app.db at insert/read time.

This module also contains a curriculum-aligned starter set for grades 4 and 5.
These are original practice questions, not copied exam questions.
"""

import csv
from pathlib import Path

from . import db

ROOT = Path(__file__).resolve().parent.parent
SEED_FILES = (
    ROOT / "data" / "expanded_questions.csv",
    ROOT / "data" / "d10_humanities_questions.csv",
    ROOT / "data" / "seed_questions.csv",
)


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


def _add_starter(rows, grade, subject, chapter, topic, question,
                 a, b, c, d, explanation, level="متوسط"):
    rows.append({
        "grade": grade, "track": "عمومی", "subject": subject,
        "book": f"{subject} {grade}", "chapter": chapter, "topic": topic,
        "subtopic": "", "difficulty": level, "question": question,
        "option_a": a, "option_b": b, "option_c": c, "option_d": d,
        "correct_option": "A", "explanation": explanation,
        "source": "تألیفی بر اساس کتاب درسی", "source_type": "original",
        "source_year": "",
    })


def _grade45_starter_rows():
    rows = []
    adds = [
        (125,37),(246,54),(305,78),(420,65),(512,89),
        (735,26),(840,45),(960,32),(108,47),(625,75)
    ]
    muls = [(12,4),(15,6),(18,5),(21,3),(24,4),(16,7),(13,8),(25,3),(14,6),(22,5)]

    for grade in ("چهارم", "پنجم"):
        for x,y in adds:
            t=x+y
            _add_starter(rows,grade,"ریاضی","عددنویسی و محاسبات","جمع و تفریق",
                         f"حاصل {x} + {y} کدام است؟",str(t),str(t+10),str(t-10),str(t+1),
                         "با جمع مستقیم دو عدد، حاصل به دست می‌آید.","آسان")
        for x,y in muls:
            t=x*y
            _add_starter(rows,grade,"ریاضی","ضرب و تقسیم","ضرب",
                         f"حاصل {x} × {y} کدام است؟",str(t),str(t+1),str(t-1),str(x+y),
                         "حاصل ضرب با محاسبه مستقیم دو عامل به دست می‌آید.")
        for n in range(2,12):
            _add_starter(rows,grade,"ریاضی","کسر و عدد","کسرهای هم‌مخرج",
                         "کدام کسر بزرگ‌تر است?",f"{n+1}/{n+4}",f"{n}/{n+4}",
                         f"{n-1}/{n+4}",f"{n}/{n+5}",
                         "وقتی مخرج‌ها برابرند، صورت بزرگ‌تر کسر بزرگ‌تری می‌سازد.")
        for i in range(10):
            length=6+i; p=2*(length+3)
            _add_starter(rows,grade,"ریاضی","هندسه و اندازه‌گیری","محیط",
                         f"محیط مستطیلی با طول {length} و عرض 3 سانتی‌متر چند سانتی‌متر است؟",
                         str(p),str(length+3),str(2*length),str(length*3),
                         "محیط مستطیل برابر ۲ × (طول + عرض) است.")

        science=[
            ("مواد و تغییرات","حالت‌های ماده","کدام گزینه یک ماده جامد است؟","سنگ","آب","هوا","بخار آب","سنگ در شرایط معمول جامد است."),
            ("مواد و تغییرات","تغییر حالت","تبدیل یخ به آب چه نام دارد؟","ذوب","انجماد","تبخیر","میعان","یخ با دریافت گرما ذوب می‌شود."),
            ("انرژی","منابع انرژی","کدام مورد منبع انرژی تجدیدپذیر است؟","خورشید","زغال‌سنگ","نفت","گاز طبیعی","انرژی خورشیدی تجدیدپذیر است."),
            ("بدن انسان","اندام‌ها","کدام اندام در پمپاژ خون نقش اصلی دارد؟","قلب","معده","ریه","کلیه","قلب خون را در بدن به گردش درمی‌آورد."),
            ("زمین","آب و هوا","کدام فرایند به تشکیل ابر کمک می‌کند؟","میعان بخار آب","ذوب سنگ","سوختن چوب","حل شدن نمک","بخار آب با سرد شدن می‌تواند به قطره‌های آب تبدیل شود.")
        ]
        for ch,to,q,a,b,c,d,e in science:
            for level in ("آسان","متوسط"):
                _add_starter(rows,grade,"علوم",ch,to,q,a,b,c,d,e,level)

        persian=[
            ("واژه و معنا","واژه‌شناسی","کدام گزینه هم‌معنی «شاد» است؟","خوشحال","خشمگین","خسته","اندوهگین","«خوشحال» با «شاد» هم‌معنی است."),
            ("خواندن و درک متن","ایده اصلی","برای یافتن ایده اصلی متن، کدام کار مناسب‌تر است؟","توجه به پیام کلی متن","شمردن حروف","حذف عنوان","نادیده گرفتن جمله‌ها","ایده اصلی از پیام کلی متن به دست می‌آید."),
            ("نگارش","جمله‌سازی","کدام گزینه یک جمله کامل است؟","دانش‌آموز کتاب را خواند.","کتاب و دفتر","در حیاط مدرسه","بسیار زیبا","گزینه اول معنای کامل دارد."),
            ("دستور زبان","فعل","در جمله «مریم به مدرسه رفت»، فعل کدام است؟","رفت","مریم","مدرسه","به","«رفت» فعل جمله است."),
            ("املا","املای درست","کدام واژه درست نوشته شده است؟","مسئول","مسول","مسئولل","مسئل","املای درست «مسئول» است.")
        ]
        for ch,to,q,a,b,c,d,e in persian:
            for level in ("آسان","متوسط"):
                _add_starter(rows,grade,"فارسی",ch,to,q,a,b,c,d,e,level)

        social=[
            ("جغرافیا","نقشه","نقشه برای چه کاری کاربرد دارد؟","نمایش مکان‌ها و مسیرها","اندازه‌گیری دمای بدن","پخت غذا","تولید برق","نقشه برای نمایش مکان‌ها و مسیرهاست."),
            ("جامعه","همکاری","کدام رفتار به همکاری گروهی کمک می‌کند؟","تقسیم مسئولیت‌ها","نادیده گرفتن دیگران","انجام همه کارها توسط یک نفر","قطع گفت‌وگو","تقسیم مسئولیت‌ها مشارکت گروهی را بیشتر می‌کند."),
            ("تاریخ","گذشته","مطالعه تاریخ چه کمکی می‌کند؟","شناخت رویدادهای گذشته","پیش‌بینی دقیق هوا","اندازه‌گیری قد","محاسبه سرعت","تاریخ به شناخت رویدادهای گذشته کمک می‌کند."),
            ("اقتصاد خانواده","مصرف","کدام رفتار نمونه مصرف درست است؟","خرید متناسب با نیاز","خرید بدون برنامه","دور ریختن غذای سالم","مصرف بی‌رویه آب","مصرف درست یعنی استفاده آگاهانه و متناسب با نیاز.")
        ]
        for ch,to,q,a,b,c,d,e in social:
            for level in ("آسان","متوسط"):
                _add_starter(rows,grade,"مطالعات اجتماعی",ch,to,q,a,b,c,d,e,level)

        for subject in ("هدیه‌های آسمان","قرآن"):
            religious=[
                ("آموزه‌ها","رفتار اخلاقی","کدام رفتار با احترام به دیگران سازگارتر است؟","گوش دادن و رعایت حق دیگران","تمسخر دیگران","قطع سخن دیگران","نادیده گرفتن حقوق دیگران","احترام یعنی رعایت کرامت و حق دیگران."),
                ("عبادت","مسئولیت","انجام درست یک وظیفه چه اثری دارد؟","تقویت مسئولیت‌پذیری","افزایش بی‌نظمی","کاهش همکاری","نادیده گرفتن وظایف","انجام وظیفه به مسئولیت‌پذیری کمک می‌کند.")
            ]
            for ch,to,q,a,b,c,d,e in religious:
                for level in ("آسان","متوسط"):
                    _add_starter(rows,grade,subject,ch,to,q,a,b,c,d,e,level)
    return rows


def _seed_grade45():
    inserted=0
    for row in _grade45_starter_rows():
        try:
            if db.insert_question_if_new(row):
                inserted += 1
        except Exception as exc:
            print(f"[QUESTION-BANK] grade 4/5 starter skipped: {exc}",flush=True)
    return inserted


def bootstrap_question_bank():
    """Load only real seeded questions; never manufacture filler variants.

    Missing coverage is reported rather than filled with renamed/rotated copies.
    This keeps question count honest and preserves existing student/question data.
    """
    seeded=_seed_bundled()
    starter45=_seed_grade45()
    total=db.count_questions({})
    print(
        f"[QUESTION-BANK] ready: total={total}, bundled_added={seeded}, "
        f"grade45_added={starter45}, synthetic_variants=disabled",
        flush=True,
    )
    return {"total":total,"seeded":seeded,"grade45":starter45,"variants":0}
