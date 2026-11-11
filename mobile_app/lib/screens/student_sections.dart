import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class StudyPlanScreen extends StatelessWidget {
  const StudyPlanScreen({super.key});
  @override
  Widget build(BuildContext context) => const _SimpleStudentPage(title: 'برنامه مطالعاتی', subtitle: 'قدم‌به‌قدم تا هدفی که براش تلاش می‌کنی', icon: Icons.calendar_month_rounded, items: ['شنبه  •  ریاضی  •  مرور و حل تمرین','یکشنبه  •  علوم  •  مطالعه درس جدید','دوشنبه  •  فارسی  •  تمرین و مرور']);
}
class TestsScreen extends StatelessWidget {
  const TestsScreen({super.key});
  @override
  Widget build(BuildContext context) => const _SimpleStudentPage(title: 'آزمون‌های من', subtitle: 'تمرین کن، یاد بگیر و پیشرفتت رو ببین', icon: Icons.quiz_rounded, items: ['آزمون تمرینی ریاضی  •  ۱۵ سؤال','مرور علوم  •  ۱۰ سؤال','آزمون مهارت‌های یادگیری  •  دانلود نشده']);
}
class DailyReportScreen extends StatefulWidget {
  const DailyReportScreen({super.key});
  @override
  State<DailyReportScreen> createState() => _DailyReportScreenState();
}
class _DailyReportScreenState extends State<DailyReportScreen> {
  double hours = 2;
  int focus = 3;
  final note = TextEditingController();
  @override
  void dispose() { note.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('گزارش روزانه'), backgroundColor: AppColors.canvas),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      const Text('هر تلاشی ارزشمنده؛ حتی قدم‌های کوچیک.', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: AppColors.ink)),
      const SizedBox(height: 18),
      const _OfflineNotice(),
      const SizedBox(height: 20),
      const Text('امروز چند ساعت مطالعه کردی؟', style: TextStyle(fontWeight: FontWeight.w800)),
      Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(children: [
        Text(hours.toStringAsFixed(1) + ' ساعت', style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w900, color: AppColors.primary)),
        Slider(value: hours, min: 0, max: 12, divisions: 24, onChanged: (v) => setState(() => hours = v)),
      ]))),
      const SizedBox(height: 18),
      const Text('تمرکز امروزت چطور بود؟', style: TextStyle(fontWeight: FontWeight.w800)),
      Wrap(spacing: 8, children: List.generate(5, (i) => ChoiceChip(label: Text(['خیلی کم','کم','متوسط','خوب','عالی'][i]), selected: focus == i + 1, onSelected: (_) => setState(() => focus = i + 1)))),
      const SizedBox(height: 18),
      const Text('یادداشت امروز', style: TextStyle(fontWeight: FontWeight.w800)),
      const SizedBox(height: 8),
      TextField(controller: note, maxLines: 3, decoration: InputDecoration(hintText: 'چه چیزی خوب پیش رفت؟ چه چیزی سخت بود؟', filled: true, fillColor: Colors.white, border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)))),
      const SizedBox(height: 18),
      FilledButton.icon(onPressed: () => ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('این فرم نمایشی است؛ ذخیره آفلاین در مرحله اتصال پایگاه داده فعال می‌شود.'))), icon: const Icon(Icons.save_rounded), label: const Text('ذخیره گزارش')),
    ]),
  );
}
class WellbeingScreen extends StatefulWidget {
  const WellbeingScreen({super.key});
  @override
  State<WellbeingScreen> createState() => _WellbeingScreenState();
}
class _WellbeingScreenState extends State<WellbeingScreen> {
  int mood = 3;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('حال خوب من'), backgroundColor: AppColors.canvas),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      const Text('اینجا می‌تونی بدون قضاوت از حال امروزت بگی.', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: AppColors.ink)),
      const SizedBox(height: 18),
      const _OfflineNotice(),
      const SizedBox(height: 22),
      const Text('امروز چه حسی داری؟', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
      const SizedBox(height: 12),
      Wrap(spacing: 8, children: List.generate(4, (i) => ChoiceChip(label: Text(['😔 گرفته','😕 معمولی','🙂 خوب','😄 شاد'][i]), selected: mood == i + 1, onSelected: (_) => setState(() => mood = i + 1)))),
      const SizedBox(height: 22),
      const Text('این بخش برای شناخت بهتر حال روزانه توست و ابزار تشخیص پزشکی یا روان‌شناختی نیست. اگر نیاز به همراهی داری، می‌تونی با مشاورت ارتباط بگیری.', style: TextStyle(fontSize: 12, height: 1.9, color: AppColors.muted)),
      const SizedBox(height: 18),
      FilledButton(onPressed: () => ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('این فرم نمایشی است؛ ذخیره امن در مرحله بعد فعال می‌شود.'))), child: const Text('ثبت حال امروز')),
    ]),
  );
}
class _SimpleStudentPage extends StatelessWidget {
  const _SimpleStudentPage({required this.title, required this.subtitle, required this.icon, required this.items});
  final String title, subtitle;
  final IconData icon;
  final List<String> items;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('ترنم همدلی', style: TextStyle(fontWeight: FontWeight.w900, color: AppColors.deepBlue)), backgroundColor: AppColors.canvas),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      Row(children: [Icon(icon, color: AppColors.primary, size: 30), const SizedBox(width: 12), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: AppColors.ink)), Text(subtitle, style: const TextStyle(color: AppColors.muted, fontSize: 12))]))]),
      const SizedBox(height: 20),
      const _OfflineNotice(),
      const SizedBox(height: 14),
      ...items.map((item) => Card(margin: const EdgeInsets.only(bottom: 10), child: ListTile(leading: const CircleAvatar(backgroundColor: AppColors.sky, child: Icon(Icons.menu_book_rounded, color: AppColors.primary)), title: Text(item, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)), trailing: const Icon(Icons.chevron_left_rounded)))),
    ]),
  );
}
class _OfflineNotice extends StatelessWidget {
  const _OfflineNotice();
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.all(13), decoration: BoxDecoration(color: const Color(0xFFEAF6F0), borderRadius: BorderRadius.circular(14)), child: const Row(children: [Icon(Icons.cloud_done_outlined, color: AppColors.success), SizedBox(width: 8), Expanded(child: Text('اطلاعات ذخیره‌شده روی گوشی در دسترس است.', style: TextStyle(color: AppColors.success, fontSize: 11)))]));
}

class StudentProfileScreen extends StatelessWidget {
  const StudentProfileScreen({super.key});
  @override
  Widget build(BuildContext context) => const _SimpleStudentPage(
    title: 'حساب من',
    subtitle: 'اطلاعات و تنظیمات حساب دانش‌آموز',
    icon: Icons.person_rounded,
    items: ['مشخصات دانش‌آموز','پایه و رشته تحصیلی','تنظیمات اعلان‌ها','حریم خصوصی و امنیت','راهنما و ارتباط با ترنم همدلی'],
  );
}
