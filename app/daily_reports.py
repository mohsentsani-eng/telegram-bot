import os, json, asyncio, re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from aiogram import F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from . import db, ai

TZ = os.getenv("DAILY_REPORT_TIMEZONE", "Asia/Tehran")
REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "21"))
REMINDER_ENABLED = os.getenv("DAILY_REPORT_ENABLED", "false").strip().lower() in {"1","true","yes","on"}

PRIMARY = ["فارسی","ریاضی","علوم","مطالعات اجتماعی","هدیه‌های آسمان","نگارش","زبان انگلیسی"]
MIDDLE = ["فارسی","ریاضی","علوم","مطالعات اجتماعی","عربی","پیام‌های آسمان","زبان انگلیسی"]
GENERAL = ["فارسی","عربی","دین و زندگی","زبان انگلیسی"]
TRACKS = {
    "ریاضی":["ریاضی","فیزیک","شیمی"],
    "تجربی":["زیست‌شناسی","شیمی","فیزیک","ریاضی","زمین‌شناسی"],
    "انسانی":["ریاضی و آمار","اقتصاد","ادبیات فارسی تخصصی","عربی تخصصی","تاریخ و جغرافیا","علوم اجتماعی","فلسفه و منطق","روان‌شناسی"],
    "هنر":["درک عمومی هنر","درک عمومی ریاضی-فیزیک","خلاقیت تصویری و تجسمی"],
    "زبان":["زبان تخصصی"],
}
QUESTIONS = [
    ("study_hours","امروز چند ساعت مطالعه کردی؟",["کمتر از ۱ ساعت","۱ تا ۲ ساعت","۲ تا ۴ ساعت","بیشتر از ۴ ساعت"]),
    ("plan_execution","چند درصد برنامه امروزت اجرا شد؟",["۰ تا ۲۵٪","۲۵ تا ۵۰٪","۵۰ تا ۷۵٪","۷۵ تا ۱۰۰٪"]),
    ("subjects","امروز روی چه درس‌هایی کار کردی؟",None),
    ("practice_count","چند تست/تمرین انجام دادی؟",None),
    ("main_problem","مهم‌ترین مشکل امروز چه بود؟",["کمبود وقت","خستگی","حواس‌پرتی","سختی درس","بی‌برنامگی","بی‌انگیزگی","مدرسه","مشکل خانوادگی","مشکل دیگر"]),
    ("satisfaction","از عملکرد امروزت راضی بودی؟",["⭐ خیلی خوب","🙂 خوب","😐 متوسط","☹️ ضعیف"]),
    ("tomorrow_goal","اگر بخواهی فقط یک چیز را فردا بهتر کنی، چیست؟",None),
]

class DailyReport(StatesGroup):
    answering = State()

def _norm_num(s):
    return str(s or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹","0123456789")).strip()

def _student_subjects(s):
    grade = s["grade"] or ""
    track = s["track"] or ""
    if grade in {"چهارم","پنجم","ششم"}: return PRIMARY
    if grade in {"هفتم","هشتم","نهم"}: return MIDDLE
    return GENERAL + TRACKS.get(track, [])

def _pct(v):
    v = str(v or "")
    if "۰ تا ۲۵" in v: return 12.5
    if "۲۵ تا ۵۰" in v: return 37.5
    if "۵۰ تا ۷۵" in v: return 62.5
    if "۷۵ تا ۱۰۰" in v: return 87.5
    return 0

def _hours(v):
    v = str(v or "")
    if "کمتر" in v: return 0.5
    if "۱ تا ۲" in v: return 1.5
    if "۲ تا ۴" in v: return 3
    if "بیشتر" in v: return 5
    try: return float(_norm_num(v).replace(",","."))
    except: return 0

def _practice(v):
    try: return max(0, int(_norm_num(v)))
    except: return 0

def _parse_subjects(text, allowed):
    raw = (text or "").replace("،",",")
    vals = [x.strip() for x in raw.split(",") if x.strip()]
    invalid = [x for x in vals if x not in allowed]
    return vals, invalid

def _status(student_id, current):
    c=db.conn()
    rows=c.execute("SELECT * FROM daily_reports WHERE student_id=? ORDER BY report_date DESC LIMIT 7",(student_id,)).fetchall()
    c.close()
    # rows do not yet include today's saved report at first evaluation in some call paths.
    if not rows: return "normal", []
    execs=[float(r["plan_execution"] or 0) for r in rows]
    problems=[r["main_problem"] for r in rows if r["main_problem"]]
    flags=[]
    if len(rows)>=3 and all(x <= 25 for x in execs[:3]):
        flags.append(("execution_drop","followup","سه گزارش اخیر اجرای برنامه بسیار پایین بوده است."))
    if len(rows)>=3 and problems and len(set(problems[:3]))==1:
        flags.append(("repeated_problem","attention",f"مشکل «{problems[0]}» در سه گزارش اخیر تکرار شده است."))
    if len(rows)>=5:
        recent=sum(execs[:3])/3; older=sum(execs[3:5])/2
        if older-recent >= 20:
            flags.append(("trend_drop","followup","اجرای برنامه نسبت به روزهای قبل افت محسوسی داشته است."))
    # Missing report detection is handled separately in reminder/follow-up dashboard.
    status="normal"
    if any(x[1]=="followup" for x in flags): status="followup"
    elif flags: status="attention"
    return status, flags

def _rule_recommendations(report, flags):
    rec=[]
    problem=report.get("main_problem","")
    if problem=="خستگی": rec.append("حجم بازه عصر را کمی کاهش بده و درس دشوارتر را به اولین بازه مطالعه منتقل کن.")
    elif problem=="حواس‌پرتی": rec.append("یک بازه ۴۵ تا ۶۰ دقیقه‌ای بدون موبایل و اعلان اجرا کن.")
    elif problem=="کمبود وقت": rec.append("فردا فقط ۳ اولویت اصلی را مشخص کن و برنامه را با زمان‌های واقعی هماهنگ کن.")
    elif problem=="بی‌برنامگی": rec.append("قبل از شروع مطالعه، سه کار اصلی فردا را به ترتیب اولویت بنویس.")
    elif problem=="بی‌انگیزگی": rec.append("هدف فردا را کوچک و قابل اندازه‌گیری کن؛ شروع کوتاه بهتر از برنامه سنگین و اجرا نشده است.")
    elif problem=="سختی درس": rec.append("درس دشوار را به بخش‌های کوچک‌تر تقسیم کن و بعد از هر بخش چند تمرین کوتاه بزن.")
    else: rec.append("یک هدف کوچک و قابل اندازه‌گیری برای فردا تعیین کن.")
    if any(f[0]=="execution_drop" for f in flags): rec.insert(0,"به‌جای جبران فشرده، فردا حجم برنامه را کمی واقعی‌تر کن و اجرای آن را پایش کن.")
    return rec[:3]

def _json_from_ai(text):
    text=(text or "").strip()
    try:
        return json.loads(text)
    except:
        m=re.search(r"{.*}", text, re.S)
        if m:
            try: return json.loads(m.group(0))
            except: pass
    return None

async def _analyze_ai(student, report, history):
    if not ai.enabled(): return None
    context={"student":{"grade":student["grade"],"track":student["track"] or ""},"today":report,"history":history}
    prompt=("فقط یک JSON معتبر و بدون markdown برگردان با کلیدهای "
            "trend, main_problem, evidence, recommendation, confidence, needs_counselor_review. "
            "هیچ تشخیص بالینی نده. فقط از داده‌های ارائه‌شده استفاده کن.")
    try:
        text=await ai.ask(prompt, context=json.dumps(context,ensure_ascii=False), max_tokens=900)
        return _json_from_ai(text)
    except Exception as exc:
        print(f"[AI] daily report analysis pending: {type(exc).__name__}: {exc}", flush=True)
        return None

def _save_report(student, answers):
    now=datetime.now(ZoneInfo(TZ))
    day=now.date().isoformat()
    hours=_hours(answers.get("study_hours"))
    execution=_pct(answers.get("plan_execution"))
    practice=_practice(answers.get("practice_count"))
    subjects=json.dumps(answers.get("subjects_list",[]),ensure_ascii=False)
    c=db.conn()
    c.execute("""INSERT INTO daily_reports(student_id,report_date,study_hours,plan_execution,subjects_json,practice_count,main_problem,satisfaction,tomorrow_goal,status,analysis_status)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(student_id,report_date) DO UPDATE SET
                 study_hours=excluded.study_hours,plan_execution=excluded.plan_execution,subjects_json=excluded.subjects_json,
                 practice_count=excluded.practice_count,main_problem=excluded.main_problem,satisfaction=excluded.satisfaction,
                 tomorrow_goal=excluded.tomorrow_goal,updated_at=CURRENT_TIMESTAMP""",
              (student["id"],day,hours,execution,subjects,practice,answers.get("main_problem",""),answers.get("satisfaction",""),answers.get("tomorrow_goal",""),"normal","pending"))
    report=c.execute("SELECT * FROM daily_reports WHERE student_id=? AND report_date=?",(student["id"],day)).fetchone()
    for k,v in answers.items():
        if k=="subjects_list": v=", ".join(answers[k])
        c.execute("INSERT INTO daily_report_answers(report_id,question_key,answer) VALUES(?,?,?) ON CONFLICT(report_id,question_key) DO UPDATE SET answer=excluded.answer",(report["id"],k,str(v)))
    c.commit(); c.close()
    return report

async def finalize_report(student, answers):
    report=_save_report(student,answers)
    status,flags=_status(student["id"],report)
    recommendations=_rule_recommendations(dict(report),flags)
    history=[dict(r) for r in db.conn().execute("SELECT * FROM daily_reports WHERE student_id=? ORDER BY report_date DESC LIMIT 7",(student["id"],)).fetchall()]
    ai_result=await _analyze_ai(student,dict(report),history)
    final_status=status
    if ai_result and ai_result.get("needs_counselor_review") and status=="normal":
        # AI may recommend review, but does not directly create a critical status.
        final_status="attention"
    analysis={"status":final_status,"trend":ai_result.get("trend") if ai_result else ("نیازمند پایش" if status!="normal" else "پایدار"),
              "main_problem":ai_result.get("main_problem") if ai_result else report["main_problem"],
              "evidence":ai_result.get("evidence",[]) if ai_result else [f"اجرای برنامه امروز: {report['plan_execution']}٪"],
              "recommendation":(ai_result.get("recommendation") if ai_result else recommendations),
              "confidence":ai_result.get("confidence") if ai_result else "local_rule_engine",
              "needs_counselor_review": bool(status in {"followup","urgent_review"} or (ai_result and ai_result.get("needs_counselor_review"))),
              "rule_flags":[{"type":x[0],"severity":x[1],"reason":x[2]} for x in flags]}
    c=db.conn()
    c.execute("UPDATE daily_reports SET status=?,analysis_status=?,analysis_json=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(final_status,"completed" if ai_result else "completed_local",json.dumps(analysis,ensure_ascii=False),report["id"]))
    c.execute("INSERT INTO student_progress(student_id,report_date,study_hours,plan_execution,practice_count,status,trend,evidence_json) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(student_id,report_date) DO UPDATE SET study_hours=excluded.study_hours,plan_execution=excluded.plan_execution,practice_count=excluded.practice_count,status=excluded.status,trend=excluded.trend,evidence_json=excluded.evidence_json",(student["id"],report["report_date"],report["study_hours"],report["plan_execution"],report["practice_count"],final_status,analysis["trend"],json.dumps(analysis.get("evidence",[]),ensure_ascii=False)))
    for f in flags:
        c.execute("INSERT INTO ai_flags(student_id,report_id,flag_type,severity,reason) VALUES(?,?,?,?,?)",(student["id"],report["id"],f[0],f[1],f[2]))
    for i,r in enumerate(recommendations,1):
        c.execute("INSERT INTO ai_recommendations(student_id,report_id,recommendation,priority,source) VALUES(?,?,?,?,?)",(student["id"],report["id"],r,i,"rule_engine"))
    if final_status in {"followup","urgent_review"}:
        c.execute("INSERT INTO followups(student_id,followup_type,priority,status,note) VALUES(?,?,?,?,?)",(student["id"],"daily_report",final_status,"open","پیگیری بر اساس گزارش روزانه"))
    c.commit(); c.close()
    return report,analysis

def _keyboard(options):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=x)] for x in options]+[[KeyboardButton(text="↩️ بازگشت"),KeyboardButton(text="🏠 منوی اصلی")]],resize_keyboard=True)

async def start_report(message,state):
    student=db.get_student_by_tg(message.from_user.id)
    if not student:
        return await message.answer("ابتدا ثبت‌نام را کامل کن.")
    await state.clear()
    await state.update_data(answers={},step=0)
    await state.set_state(DailyReport.answering)
    await message.answer("🌙 <b>گزارش امروز</b>

فقط ۲ دقیقه زمان می‌برد.

سؤال ۱ از ۷:
امروز چند ساعت مطالعه کردی؟",reply_markup=_keyboard(QUESTIONS[0][2]))

async def answer_report(message,state):
    if message.text in {"↩️ بازگشت","🏠 منوی اصلی"}:
        await state.clear(); return await message.answer("🏠 منوی اصلی",reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🌙 گزارش امروز")]],resize_keyboard=True))
    data=await state.get_data(); step=int(data.get("step",0)); answers=dict(data.get("answers",{}))
    student=db.get_student_by_tg(message.from_user.id)
    if not student: await state.clear(); return
    key,prompt,options=QUESTIONS[step]
    val=(message.text or "").strip()
    if key=="subjects":
        allowed=_student_subjects(student); vals,invalid=_parse_subjects(val,allowed)
        if invalid or not vals:
            return await message.answer("فقط از این درس‌ها استفاده کن:
"+"، ".join(allowed))
        answers["subjects_list"]=vals
    elif key=="practice_count":
        if not _norm_num(val).isdigit(): return await message.answer("لطفاً تعداد تست/تمرین را فقط به عدد وارد کن.")
        answers[key]=val
    elif options and val not in options:
        return await message.answer("لطفاً یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کن.",reply_markup=_keyboard(options))
    else: answers[key]=val
    nxt=step+1
    if nxt < len(QUESTIONS):
        await state.update_data(answers=answers,step=nxt)
        k,p,o=QUESTIONS[nxt]
        if k=="subjects":
            o=_student_subjects(student)
            return await message.answer(f"سؤال {nxt+1} از ۷:
{p}

درس‌ها را با «،» جدا کن.",reply_markup=_keyboard(o))
        if o: return await message.answer(f"سؤال {nxt+1} از ۷:
{p}",reply_markup=_keyboard(o))
        return await message.answer(f"سؤال {nxt+1} از ۷:
{p}",reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="↩️ بازگشت"),KeyboardButton(text="🏠 منوی اصلی")]],resize_keyboard=True))
    await state.clear()
    await message.answer("✅ گزارش امروز ثبت شد. در حال تحلیل روندت هستم...",reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 منوی اصلی")]],resize_keyboard=True))
    report,analysis=await finalize_report(student,answers)
    status=analysis["status"]
    label={"normal":"🟢 مناسب","attention":"🟡 توجه","followup":"🟠 پیگیری","urgent_review":"🔴 بررسی سریع"}.get(status,status)
    rec=analysis.get("recommendation") or []
    if isinstance(rec,str): rec=[rec]
    text=f"📊 <b>تحلیل امروز</b>

⏱️ مطالعه: {report['study_hours']:g} ساعت
📈 اجرای برنامه: {report['plan_execution']:g}%
📌 وضعیت: {label}

"
    if analysis.get("trend"): text+=f"روند: {analysis['trend']}
"
    if analysis.get("main_problem"): text+=f"⚠️ مسئله اصلی: {analysis['main_problem']}
"
    text+="
🎯 پیشنهادها:
" + "
".join(f"• {x}" for x in rec[:3])
    if analysis.get("needs_counselor_review"):
        text+="

👨‍🏫 این گزارش برای پیگیری مشاور علامت‌گذاری شد."
    await message.answer(text,reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🌙 گزارش امروز")],[KeyboardButton(text="🏠 منوی اصلی")]],resize_keyboard=True))

async def nightly_reminder_loop(bot):
    if not REMINDER_ENABLED:
        return
    last_day=None
    while True:
        try:
            now=datetime.now(ZoneInfo(TZ))
            day=now.date().isoformat()
            if now.hour==REPORT_HOUR and now.minute < 5 and day!=last_day:
                c=db.conn()
                students=c.execute("SELECT id,telegram_id,first_name FROM students WHERE registered=1 AND telegram_id IS NOT NULL").fetchall()
                for s in students:
                    existing=c.execute("SELECT id FROM daily_reports WHERE student_id=? AND report_date=?",(s["id"],day)).fetchone()
                    if existing: continue
                    cur=c.execute("INSERT OR IGNORE INTO notifications(student_id,kind,scheduled_for,payload_json) VALUES(?,?,?,?,?)",(s["id"],"daily_report_reminder",day,json.dumps({"hour":REPORT_HOUR},ensure_ascii=False)))
                    if cur.rowcount:
                        try:
                            await bot.send_message(s["telegram_id"],"🌙 وقت گزارش امروزته
فقط ۲ دقیقه زمان می‌بره.",reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🌙 گزارش امروز")]],resize_keyboard=True))
                            c.execute("UPDATE notifications SET sent_at=CURRENT_TIMESTAMP,status='sent' WHERE id=?",(cur.lastrowid,))
                        except Exception as exc:
                            c.execute("UPDATE notifications SET status='error',payload_json=? WHERE id=?",(json.dumps({"error":str(exc)[:200]},ensure_ascii=False),cur.lastrowid))
                c.commit(); c.close()
                last_day=day
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[REPORT] reminder loop error: {type(exc).__name__}: {exc}",flush=True)
            await asyncio.sleep(60)

def register(dp, bot):
    @dp.message(F.text=="🌙 گزارش امروز")
    async def _start(message:Message,state:FSMContext):
        await start_report(message,state)
    @dp.message(DailyReport.answering)
    async def _answer(message:Message,state:FSMContext):
        await answer_report(message,state)
    return asyncio.create_task(nightly_reminder_loop(bot)) if REMINDER_ENABLED else None
