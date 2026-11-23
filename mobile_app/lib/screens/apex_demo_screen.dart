import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Isolated preview: no authentication, student IDs, API calls, or uploads.
class ApexDemoScreen extends StatefulWidget {
  const ApexDemoScreen({super.key});
  @override
  State<ApexDemoScreen> createState() => _ApexDemoScreenState();
}

class _ApexDemoScreenState extends State<ApexDemoScreen> {
  int tab = 0;
  final subject = TextEditingController();
  final List<String> activities = [];
  int minutes = 45;

  @override
  void dispose() {
    subject.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Directionality(
    textDirection: TextDirection.rtl,
    child: Scaffold(
      appBar: AppBar(title: const Text('Apex360 | ترنم همدلی')),
      body: SafeArea(child: ListView(padding: const EdgeInsets.all(18), children: [
        Container(padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: AppColors.sky, borderRadius: BorderRadius.circular(14)),
          child: const Text('حالت نمایشی آفلاین • بدون اتصال به سرور و بدون پرونده واقعی دانش‌آموز. اطلاعات این صفحه فقط تا زمان بسته‌شدن برنامه نگهداری می‌شود.',
            style: TextStyle(fontSize: 12, height: 1.8))),
        const SizedBox(height: 16),
        if (tab == 0) ...[
          const Text('سلام! به مسیر پیشرفتت خوش آمدی 🌱', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          const Card(child: ListTile(title: Text('برنامه امروز'), subtitle: Text('برای مشاهده برنامه نمونه، بخش برنامه را انتخاب کن.'), leading: Icon(Icons.calendar_month))),
          Card(child: ListTile(title: const Text('گزارش فعالیت‌ها'), subtitle: Text('${activities.length} فعالیت نمایشی ثبت شده'), leading: const Icon(Icons.insights))),
          const Card(child: ListTile(title: Text('همراهی مشاور'), subtitle: Text('در نسخه نمایشی غیرفعال است.'), leading: Icon(Icons.support_agent))),
        ],
        if (tab == 1) ...[
          const Text('برنامه مطالعاتی نمونه', style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold)),
          for (final task in ['ریاضی • مرور ۳۰ دقیقه', 'زیست • مطالعه ۴۵ دقیقه', 'فارسی • تمرین ۲۰ دقیقه'])
            Card(child: ListTile(title: Text(task), leading: const Icon(Icons.check_circle_outline))),
        ],
        if (tab == 2) ...[
          const Text('آزمون‌های نمونه', style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold)),
          const Card(child: ListTile(title: Text('آزمون تمرینی ریاضی'), subtitle: Text('فقط نمایش؛ آزمون واقعی هنوز فعال نیست'))),
          const Card(child: ListTile(title: Text('مهارت‌های یادگیری'), subtitle: Text('فقط نمایش؛ نتیجه‌ای ذخیره نمی‌شود'))),
        ],
        if (tab == 3) ...[
          const Text('ثبت فعالیت نمایشی', style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold)),
          TextField(controller: subject, decoration: const InputDecoration(labelText: 'نام درس')),
          const SizedBox(height: 14),
          Text('مدت مطالعه: $minutes دقیقه'),
          Slider(value: minutes.toDouble(), min: 15, max: 180, divisions: 11,
            onChanged: (v) => setState(() => minutes = v.round())),
          FilledButton(onPressed: () {
            if (subject.text.trim().isEmpty) return;
            setState(() => activities.insert(0, '${subject.text.trim()} • $minutes دقیقه'));
            subject.clear();
          }, child: const Text('ثبت آزمایشی (فقط در حافظه موقت)')),
          for (final item in activities) Card(child: ListTile(title: Text(item))),
        ],
        if (tab == 4) ...[
          const Text('حساب نمایشی', style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold)),
          const Card(child: ListTile(title: Text('دانش‌آموز نمونه'), subtitle: Text('هیچ اطلاعات واقعی دریافت نشده است'))),
          const Card(child: ListTile(title: Text('اتصال به تلگرام'), subtitle: Text('در حالت نمایشی غیرفعال است'))),
        ],
      ])),
      bottomNavigationBar: NavigationBar(selectedIndex: tab,
        onDestinationSelected: (value) => setState(() => tab = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: 'خانه'),
          NavigationDestination(icon: Icon(Icons.calendar_month_outlined), label: 'برنامه'),
          NavigationDestination(icon: Icon(Icons.quiz_outlined), label: 'آزمون'),
          NavigationDestination(icon: Icon(Icons.insights_outlined), label: 'گزارش'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'حساب'),
        ]),
    ),
  );
}
