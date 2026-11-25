import 'dart:convert';
import 'package:shamsi_date/shamsi_date.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Offline-only workspace; does not contact the production bot or API.
class ApexDemoScreen extends StatefulWidget {
  const ApexDemoScreen({super.key});
  @override
  State<ApexDemoScreen> createState() => _ApexDemoScreenState();
}
class _ApexDemoScreenState extends State<ApexDemoScreen> {
  static const storageKey = 'apex360_offline_v1';
  final taskController = TextEditingController();
  final subjectController = TextEditingController();
  final topicController = TextEditingController();
  final noteController = TextEditingController();
  int plannedMinutes = 60, priority = 2;
  int? linkedTaskIndex;
  int? editingTaskIndex;
  int planFormVersion = 0;
  String? filterDay;
  bool completeLinkedTask = false;
  int reportFormVersion = 0;
  int? editingReportIndex;
  DateTime selectedDate = DateTime.now();
  String get selectedDay => selectedDate.toIso8601String().substring(0, 10);
  int tab = 0, minutes = 45, tests = 0, satisfaction = 7, mood = 3, stress = 3;
  bool ready = false;
  bool loadFailed = false;
  final nameController = TextEditingController();
  final gradeController = TextEditingController();
  final trackController = TextEditingController();
  String studentName = '', studentGrade = '', studentTrack = '';
  List<Map<String, dynamic>> tasks = [], reports = [];
  String persianDate(String raw) {
    final date = DateTime.tryParse(raw);
    if (date == null) return raw;
    final j = Jalali.fromDateTime(date);
    return '${j.year}/${j.month.toString().padLeft(2, '0')}/${j.day.toString().padLeft(2, '0')}';
  }
  String get today => DateTime.now().toIso8601String().substring(0, 10);

  @override
  void initState() { super.initState(); load(); }
  Future<void> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(storageKey);
      if (raw != null) {
        final data = jsonDecode(raw) as Map<String, dynamic>;
        studentName = data['studentName']?.toString() ?? '';
        studentGrade = data['studentGrade']?.toString() ?? '';
        studentTrack = data['studentTrack']?.toString() ?? '';
        nameController.text = studentName;
        gradeController.text = studentGrade;
        trackController.text = studentTrack;
        tasks = (data['tasks'] as List<dynamic>).map((v) => Map<String, dynamic>.from(v as Map)).toList();
        reports = (data['reports'] as List<dynamic>).map((v) => Map<String, dynamic>.from(v as Map)).toList();
      }
      if (mounted) setState(() => ready = true);
    } catch (_) {
      if (mounted) setState(() => loadFailed = true);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('خواندن داده‌ها ممکن نشد. برای حفاظت از اطلاعات، ثبت غیرفعال است.')));
    }
  }
  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    final success = await prefs.setString(storageKey, jsonEncode({'tasks': tasks, 'reports': reports, 'studentName': studentName, 'studentGrade': studentGrade, 'studentTrack': studentTrack}));
    if (!success && mounted) ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('ذخیره اطلاعات ناموفق بود.')));
  }
  Future<void> addTask() async {
    final name = taskController.text.trim();
    if (name.isEmpty) return;
    setState(() {
      final task = <String, dynamic>{'title': name, 'topic': topicController.text.trim(), 'date': selectedDay, 'plannedMinutes': plannedMinutes, 'priority': priority, 'done': false};
      if (editingTaskIndex != null) {
        final i = editingTaskIndex!;
        tasks[i] = {...tasks[i], ...task, 'done': tasks[i]['done']};
      } else { tasks.insert(0, task); }
      editingTaskIndex = null;
      linkedTaskIndex = null;
      completeLinkedTask = false;
      reportFormVersion++;
      planFormVersion++;
    });
    taskController.clear();
    topicController.clear();
    await save();
  }
  String canonicalSubject(String value) {
    final name = value.trim().replaceAll('ي', 'ی').replaceAll('ك', 'ک');
    return name == 'ریاضیات' ? 'ریاضی' : name;
  }
  void resetReport() {
    editingReportIndex = null; linkedTaskIndex = null; completeLinkedTask = false;
    subjectController.clear(); noteController.clear();
    minutes = 45; tests = 0; satisfaction = 7; mood = 3; stress = 3; reportFormVersion++;
  }
  Future<void> addReport() async {
    final name = canonicalSubject(subjectController.text);
    if (name.isEmpty) return;
    final linked = linkedTaskIndex == null ? null : tasks[linkedTaskIndex!];
    setState(() {
      if (linked != null && completeLinkedTask) linked['done'] = true;
      final previous = editingReportIndex == null ? null : reports[editingReportIndex!];
      final report = <String, dynamic>{...?previous, 'subject': name, 'date': previous?['date'] ?? today, 'linkedTitle': linked?['title'] ?? previous?['linkedTitle'], 'linkedDate': linked?['date'] ?? previous?['linkedDate'],
      'minutes': minutes, 'tests': tests, 'satisfaction': satisfaction,
      'mood': mood, 'stress': stress, 'note': noteController.text.trim()};
      if (editingReportIndex == null) { reports.insert(0, report); } else { reports[editingReportIndex!] = report; }
      editingReportIndex = null;
    });
    subjectController.clear();
    noteController.clear();
    setState(resetReport);
    await save();
  }
  @override
  void dispose() { taskController.dispose(); subjectController.dispose(); topicController.dispose(); noteController.dispose(); nameController.dispose(); gradeController.dispose(); trackController.dispose(); super.dispose(); }
  Widget heading(String label) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Text(label, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)));

  Widget home() {
    final current = tasks.where((t) => t['date'] == today).toList();
    final done = current.where((t) => t['done'] == true).length;
    final currentReports = reports.where((r) => r['date'] == today).toList();
    final total = currentReports.fold<int>(0, (sum, r) => sum + (r['minutes'] as int));
    final count = currentReports.fold<int>(0, (sum, r) => sum + (r['tests'] as int));
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Container(
        padding: const EdgeInsets.all(18),
        margin: const EdgeInsets.only(bottom: 16),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF174C75), Color(0xFF167D82)]),
          borderRadius: BorderRadius.circular(22)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('مسیر پیشرفت من', style: TextStyle(color: Colors.white70, fontSize: 14)),
          const SizedBox(height: 8),
          Text(studentName.isEmpty ? 'به Apex360 خوش آمدی' : 'سلام، $studentName', style: const TextStyle(color: Colors.white, fontSize: 23, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(persianDate(today), style: const TextStyle(color: Colors.white)),
          const SizedBox(height: 12),
          LinearProgressIndicator(value: current.isEmpty ? 0 : done / current.length, color: Colors.white, backgroundColor: Colors.white24),
          const SizedBox(height: 8),
          Text('امروز $done از ${current.length} تکلیف انجام شده', style: const TextStyle(color: Colors.white)),
        ])),
      if (studentName.isEmpty || studentGrade.isEmpty)
        Card(child: ListTile(leading: const Icon(Icons.person_add_alt_1), title: const Text('تکمیل پروفایل دانش‌آموز'), subtitle: const Text('نام و پایه تحصیلی خود را ثبت کن.'), onTap: () => setState(() => tab = 4))),
      heading(studentName.isEmpty ? 'سلام! امروز چه قدمی برای پیشرفتت برداشتی؟ 🌱' : 'سلام $studentName! امروز چه قدمی برای پیشرفتت برداشتی؟ 🌱'),
      Card(child: ListTile(title: const Text('اجرای برنامه امروز'),
        subtitle: LinearProgressIndicator(value: current.isEmpty ? 0 : done / current.length),
        trailing: Text(done.toString() + ' از ' + current.length.toString()))),
      Card(child: ListTile(title: const Text('مطالعه امروز'), trailing: Text(total.toString() + ' دقیقه'))),
      Card(child: ListTile(title: const Text('تست‌های امروز'), trailing: Text(count.toString() + ' تست'))),
      FilledButton.icon(onPressed: () => setState(() { selectedDate = DateTime.now(); filterDay = today; tab = 1; }), icon: const Icon(Icons.calendar_today), label: const Text('برنامه‌ریزی امروز')),
      OutlinedButton.icon(onPressed: () => setState(() => tab = 3), icon: const Icon(Icons.edit_note), label: const Text('ثبت گزارش مطالعه')),
      heading('تکالیف امروز'),
      if (current.isEmpty) const Text('هنوز تکلیفی برای امروز ثبت نشده است.'),
      ...current.map((t) => Card(child: CheckboxListTile(title: Text(t['title'].toString()), subtitle: Text('${t["plannedMinutes"] ?? 0} دقیقه'), value: t['done'] == true, onChanged: (v) async { setState(() => t['done'] = v ?? false); await save(); }))),
    ]);
  }
  Future<DateTime?> pickJalaliDate() async {
    final initial = Jalali.fromDateTime(selectedDate);
    int year = initial.year, month = initial.month, day = initial.day;
    const months = ['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
    const weekdays = ['ش','ی','د','س','چ','پ','ج'];
    return showDialog<DateTime>(context: context, builder: (ctx) => StatefulBuilder(builder: (ctx, refresh) {
      final first = Jalali(year, month, 1);
      final count = first.monthLength;
      final offset = (first.toDateTime().weekday + 1) % 7;
      void move(int delta) {
        final next = month + delta;
        final y = next == 0 ? year - 1 : next == 13 ? year + 1 : year;
        if (y < 1402 || y > 1415) return;
        refresh(() {
          year = y; month = next == 0 ? 12 : next == 13 ? 1 : next;
          day = day.clamp(1, Jalali(year, month, 1).monthLength).toInt();
        });
      }
      return AlertDialog(
        title: const Text('انتخاب تاریخ شمسی'),
        content: SizedBox(width: 320, child: Column(mainAxisSize: MainAxisSize.min, children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            IconButton(onPressed: () => move(-1), icon: const Icon(Icons.chevron_right), tooltip: 'ماه قبل'),
            Text('${months[month - 1]} $year'),
            IconButton(onPressed: () => move(1), icon: const Icon(Icons.chevron_left), tooltip: 'ماه بعد'),
          ]),
          Row(children: weekdays.map((w) => Expanded(child: Center(child: Text(w)))).toList()),
          GridView.builder(shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 7),
            itemCount: offset + count,
            itemBuilder: (context, i) {
              final d = i - offset + 1;
              if (d < 1) return const SizedBox.shrink();
              return InkWell(onTap: () => refresh(() => day = d),
                child: Center(child: CircleAvatar(radius: 15,
                  backgroundColor: day == d ? Theme.of(context).colorScheme.primary : Colors.transparent,
                  foregroundColor: day == d ? Theme.of(context).colorScheme.onPrimary : Theme.of(context).colorScheme.onSurface,
                  child: Text('$d'))));
            }),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('انصراف')),
          TextButton(onPressed: () => Navigator.pop(ctx, DateTime.now()), child: const Text('امروز')),
          FilledButton(onPressed: () => Navigator.pop(ctx, Jalali(year, month, day).toDateTime()), child: const Text('تأیید')),
        ],
      );
    }));
  }
  Widget plan() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    heading('برنامه مطالعاتی روزانه'),
    TextField(controller: taskController, maxLength: 100,
      decoration: const InputDecoration(labelText: 'درس یا تکلیف', hintText: 'مثلاً مرور زیست')),
    TextField(controller: topicController, maxLength: 100,
      decoration: const InputDecoration(labelText: 'مبحث یا نوع فعالیت', hintText: 'مثلاً تست فصل دوم')),
    OutlinedButton.icon(onPressed: () async {
      final picked = await pickJalaliDate();
      if (picked != null && mounted) setState(() => selectedDate = picked);
    }, icon: const Icon(Icons.event), label: Text('تاریخ برنامه: ' + persianDate(selectedDay))),
    Text('زمان پیش‌بینی‌شده: ' + plannedMinutes.toString() + ' دقیقه'),
    Row(children: [const Text('ورود دقیق (دقیقه): '),
      Expanded(child: TextFormField(key: ValueKey(planFormVersion), initialValue: plannedMinutes.toString(),
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(hintText: 'دقیقه'),
        onChanged: (v) { final n = int.tryParse(v); if (n != null && n >= 0 && n <= 600) setState(() => plannedMinutes = n); },
      ))]),
    Slider(value: plannedMinutes.clamp(0, 240).toDouble(), min: 0, max: 240, divisions: 16,
      onChanged: (v) => setState(() { plannedMinutes = v.round(); planFormVersion++; })),
    Text('اولویت: ' + (priority == 1 ? 'زیاد' : priority == 2 ? 'متوسط' : 'کم')),
    SegmentedButton<int>(segments: const [
      ButtonSegment(value: 1, label: Text('زیاد')),
      ButtonSegment(value: 2, label: Text('متوسط')),
      ButtonSegment(value: 3, label: Text('کم')),
    ], selected: {priority}, onSelectionChanged: (v) => setState(() => priority = v.first)),
    FilledButton(onPressed: addTask, child: Text(editingTaskIndex == null ? 'افزودن به برنامه' : 'ذخیره تغییرات')),
    if (editingTaskIndex != null) TextButton(onPressed: () => setState(() {
      editingTaskIndex = null; taskController.clear(); topicController.clear(); planFormVersion++;
    }), child: const Text('انصراف از ویرایش')),
    heading('نمای هفتگی برنامه'),
    Wrap(spacing: 6, runSpacing: 6, children: [
      ChoiceChip(label: const Text('همه'), selected: filterDay == null, onSelected: (_) => setState(() => filterDay = null)),
      ...List.generate(7, (i) {
        final now = DateTime.now();
        final day = DateTime(now.year, now.month, now.day - (now.weekday + 1) % 7 + i);
        final date = day.toIso8601String().substring(0, 10);
        final count = tasks.where((t) => t['date'] == date).length;
        final done = tasks.where((t) => t['date'] == date && t['done'] == true).length;
        final label = ['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه'][i];
        return ChoiceChip(label: Text('$label $done/$count'), selected: filterDay == date,
          onSelected: (_) => setState(() => filterDay = date));
      }),
    ]),
    if (!tasks.any((t) => filterDay == null || t['date'] == filterDay)) const Text('برای این بازه تکلیفی ثبت نشده است.'),
    ...tasks.asMap().entries.where((entry) => filterDay == null || entry.value['date'] == filterDay).map((entry) => Card(child: Column(children: [CheckboxListTile(
      title: Text(entry.value['title'] as String),
      subtitle: Text(persianDate(entry.value['date'].toString()) +
        ' • ' + (entry.value['topic'] ?? '').toString() +
        ' • ' + (entry.value['plannedMinutes'] ?? 'نامشخص').toString() + ' دقیقه'),
      value: entry.value['done'] == true,
      onChanged: (value) async {
        setState(() => tasks[entry.key]['done'] = value ?? false);
        await save();
      }),
      Row(mainAxisAlignment: MainAxisAlignment.end, children: [
        TextButton.icon(icon: const Icon(Icons.edit_outlined), label: const Text('ویرایش'), onPressed: () => setState(() {
          editingTaskIndex = entry.key;
          taskController.text = entry.value['title'].toString();
          topicController.text = (entry.value['topic'] ?? '').toString();
          selectedDate = DateTime.tryParse(entry.value['date'].toString()) ?? DateTime.now();
          plannedMinutes = (entry.value['plannedMinutes'] as num?)?.toInt() ?? 60;
          priority = (entry.value['priority'] as num?)?.toInt() ?? 2;
          planFormVersion++;
        })),
        TextButton.icon(icon: const Icon(Icons.delete_outline), label: const Text('حذف'), onPressed: () async {
          final confirmed = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
            title: const Text('حذف تکلیف؟'), content: const Text('گزارش‌های مطالعه حذف نمی‌شوند.'), actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('انصراف')),
              TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('حذف'))]));
          if (confirmed != true || !mounted) return;
          setState(() { tasks.removeAt(entry.key); editingTaskIndex = null; linkedTaskIndex = null; completeLinkedTask = false; reportFormVersion++; });
          await save();
        }),
      ])]))),
  ]);
  Widget report() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    heading('ثبت گزارش روزانه'),
    if (tasks.isNotEmpty) DropdownButtonFormField<int>(
      isExpanded: true,
      key: ValueKey(reportFormVersion),
      initialValue: linkedTaskIndex,
      decoration: const InputDecoration(labelText: 'اتصال گزارش به تکلیف برنامه'),
      items: [const DropdownMenuItem<int>(value: -1, child: Text('بدون اتصال')),
        ...tasks.asMap().entries.map((e) => DropdownMenuItem<int>(value: e.key,
          child: Text(e.value['title'].toString() + ' • ' + persianDate(e.value['date'].toString()), overflow: TextOverflow.ellipsis)))],
      onChanged: (v) => setState(() {
        linkedTaskIndex = v == -1 ? null : v;
        completeLinkedTask = false;
        if (linkedTaskIndex != null) subjectController.text = tasks[linkedTaskIndex!]['title'].toString();
      }),
    ),
    if (linkedTaskIndex != null) CheckboxListTile(
      title: const Text('این تکلیف را کامل انجام دادم'),
      value: completeLinkedTask,
      onChanged: (v) => setState(() => completeLinkedTask = v ?? false)),
    TextField(controller: subjectController, maxLength: 80,
      decoration: const InputDecoration(labelText: 'نام درس')),
    Text('مدت مطالعه: ' + minutes.toString() + ' دقیقه'),
    Row(children: [const Text('ورود دقیق (دقیقه): '),
      Expanded(child: TextFormField(key: ValueKey('minutes-$reportFormVersion'), initialValue: minutes.toString(),
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(hintText: 'دقیقه'),
        onChanged: (v) { final n = int.tryParse(v); if (n != null && n >= 0 && n <= 600) setState(() => minutes = n); },
      ))]),
    Slider(value: minutes.clamp(0, 180).toDouble(), min: 0, max: 180, divisions: 12,
      onChanged: (value) => setState(() { minutes = value.round(); reportFormVersion++; })),
    TextFormField(key: ValueKey('tests-$reportFormVersion'), initialValue: tests.toString(), keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'تعداد تست (۰ تا ۱۰۰)'), onChanged: (v) { final n = int.tryParse(v); if (n != null && n >= 0 && n <= 100) setState(() => tests = n); }),
    Slider(value: tests.toDouble(), min: 0, max: 100, divisions: 100,
      onChanged: (value) => setState(() { tests = value.round(); reportFormVersion++; })),
    Text('رضایت از عملکرد: ' + satisfaction.toString() + ' از ۱۰'),
    Slider(value: satisfaction.toDouble(), min: 0, max: 10, divisions: 10,
      onChanged: (value) => setState(() => satisfaction = value.round())),
    Text('خلق امروز: ' + mood.toString() + ' از ۵'),
    Slider(value: mood.toDouble(), min: 1, max: 5, divisions: 4,
      onChanged: (value) => setState(() => mood = value.round())),
    Text('استرس امروز: ' + stress.toString() + ' از ۵'),
    Slider(value: stress.toDouble(), min: 1, max: 5, divisions: 4,
      onChanged: (value) => setState(() => stress = value.round())),
    TextField(controller: noteController, maxLines: 3, maxLength: 400,
      decoration: const InputDecoration(labelText: 'کارهای انجام‌نشده و علت آن / توضیحات')),
    FilledButton(onPressed: addReport, child: Text(editingReportIndex == null ? 'ذخیره گزارش روی گوشی' : 'ذخیره اصلاحات گزارش')),
    if (editingReportIndex != null) TextButton(onPressed: () => setState(resetReport), child: const Text('انصراف از ویرایش گزارش')),
    const SizedBox(height: 16),
    heading('گزارش‌های ثبت‌شده'),
    ...reports.asMap().entries.take(30).map((entry) { final r = entry.value; return Card(child: ListTile(
      title: Text(r['subject'].toString() + ' • ' + r['minutes'].toString() + ' دقیقه • ' + r['tests'].toString() + ' تست'),
      subtitle: Text(persianDate(r['date'].toString()) + ' | رضایت ' + r['satisfaction'].toString() + '/۱۰ | خلق ' + r['mood'].toString() + '/۵ | استرس ' + r['stress'].toString() + '/۵'),
      trailing: Row(mainAxisSize: MainAxisSize.min, children: [IconButton(icon: const Icon(Icons.delete_outline), tooltip: 'حذف گزارش', onPressed: () async {
        final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(title: const Text('حذف گزارش؟'), content: const Text('این گزارش حذف می‌شود؛ وضعیت تکلیف تغییر نمی‌کند.'), actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('انصراف')), TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('حذف'))]));
        if (ok != true || !mounted) return;
        setState(() { reports.removeAt(entry.key); resetReport(); }); await save();
      }), IconButton(icon: const Icon(Icons.edit_outlined), tooltip: 'ویرایش گزارش', onPressed: () => setState(() {
        editingReportIndex = entry.key; subjectController.text = r['subject'].toString(); noteController.text = (r['note'] ?? '').toString();
        minutes = (r['minutes'] as num).toInt(); tests = (r['tests'] as num).toInt(); satisfaction = (r['satisfaction'] as num).toInt(); mood = (r['mood'] as num).toInt(); stress = (r['stress'] as num).toInt();
        linkedTaskIndex = null; completeLinkedTask = false; reportFormVersion++;
      }))]))); }),
  ]);
  Widget progress() {
    final now = DateTime.now();
    final days = List.generate(7, (i) {
      final date = now.subtract(Duration(days: 6 - i)).toIso8601String().substring(0, 10);
      final sum = reports.where((r) => r['date'] == date).fold<int>(0, (n, r) => n + (r['minutes'] as int));
      return (date: date, sum: sum);
    });
    final total = days.fold<int>(0, (n, d) => n + d.sum);
    final maximum = days.fold<int>(60, (n, d) => d.sum > n ? d.sum : n);
    final recentDates = days.map((d) => d.date).toSet();
    final recentTasks = tasks.where((t) => recentDates.contains(t['date'])).toList();
    final completed = recentTasks.where((t) => t['done'] == true).length;
    final planned = recentTasks.fold<int>(0, (n, t) => n + ((t['plannedMinutes'] as num?)?.toInt() ?? 0));
    final bySubject = <String, int>{};
    final testsBySubject = <String, int>{};
    for (final r in reports.where((r) => recentDates.contains(r['date']))) {
      final name = canonicalSubject(r['subject'].toString());
      bySubject.update(name, (v) => v + (r['minutes'] as int), ifAbsent: () => r['minutes'] as int);
      testsBySubject.update(name, (v) => v + (r['tests'] as int), ifAbsent: () => r['tests'] as int);
    }
    final percent = recentTasks.isEmpty ? 0 : (100 * completed / recentTasks.length).round();
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      heading('پیشرفت هفت روز گذشته'),
      Card(child: ListTile(title: const Text('مجموع مطالعه هفتگی'),
        trailing: Text((total / 60).toStringAsFixed(1) + ' ساعت'))),
      Card(child: ListTile(title: const Text('پایبندی به برنامه هفتگی'),
        subtitle: Text(recentTasks.isEmpty ? 'هنوز برنامه‌ای ثبت نشده' : completed.toString() + ' تکلیف از ' + recentTasks.length.toString()),
        trailing: Text(recentTasks.isEmpty ? '—' : percent.toString() + '٪'))),
      Card(child: ListTile(title: const Text('زمان برنامه‌ریزی‌شده هفتگی'),
        trailing: Text(planned.toString() + ' دقیقه'))),
      heading('کیفیت عملکرد و حال عمومی'),
      if (reports.where((r) => recentDates.contains(r['date'])).isEmpty)
        const Text('برای مشاهده روند، گزارش مطالعه ثبت کنید.'),
      ...['satisfaction', 'mood', 'stress'].map((key) {
        final values = reports.where((r) => recentDates.contains(r['date']) && r[key] is num).map((r) => (r[key] as num).toDouble()).toList();
        final limit = key == 'satisfaction' ? 10 : 5;
        final label = key == 'satisfaction' ? 'رضایت از عملکرد' : key == 'mood' ? 'خلق خودگزارش‌شده' : 'استرس خودگزارش‌شده';
        final average = values.isEmpty ? 0.0 : values.reduce((a, b) => a + b) / values.length;
        return Card(child: ListTile(title: Text(label),
          subtitle: values.isEmpty ? const Text('داده کافی نیست') : LinearProgressIndicator(value: (average / limit).clamp(0.0, 1.0).toDouble()),
          trailing: Text(values.isEmpty ? '—' : '${average.toStringAsFixed(1)} از $limit')));
      }),
      const Text('این شاخص‌ها میانگین گزارش‌های شخصی هستند و تشخیص روان‌شناختی محسوب نمی‌شوند.'),
      heading('عملکرد به تفکیک درس'),
      if (bySubject.isEmpty) const Text('هنوز گزارشی در این هفته ثبت نشده است.'),
      ...bySubject.entries.map((e) => Card(child: ListTile(
        title: Text(e.key),
        subtitle: Text('${testsBySubject[e.key]} تست'),
        trailing: Text('${e.value} دقیقه')))),
      heading('روند مطالعه روزانه'),
      ...days.map((d) => Padding(padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(children: [
          SizedBox(width: 60, child: Text(persianDate(d.date).substring(5))),
          Expanded(child: LinearProgressIndicator(value: d.sum / maximum, minHeight: 12)),
          SizedBox(width: 75, child: Text(d.sum.toString() + ' دقیقه')),
        ]))),
    ]);
  }
  Future<void> exportBackup() async {
    final payload = jsonEncode({'format': 'apex360-backup-v1', 'tasks': tasks, 'reports': reports, 'studentName': studentName, 'studentGrade': studentGrade, 'studentTrack': studentTrack});
    await Clipboard.setData(ClipboardData(text: payload));
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('نسخه پشتیبان کپی شد. آن را در محلی خصوصی ذخیره کنید؛ شامل اطلاعات شخصی است.')));
  }
  Future<void> restoreBackup() async {
    final clip = await Clipboard.getData(Clipboard.kTextPlain);
    if (!mounted) return;
    try {
      final raw = clip?.text ?? '';
      if (raw.length > 5000000) throw const FormatException();
      final data = jsonDecode(raw) as Map<String, dynamic>;
      if (data['format'] != 'apex360-backup-v1') throw const FormatException();
      final newTasks = (data['tasks'] as List).map((v) => Map<String, dynamic>.from(v as Map)).toList();
      final newReports = (data['reports'] as List).map((v) => Map<String, dynamic>.from(v as Map)).toList();
      for (final t in newTasks) {
        if (t['plannedMinutes'] != null && (t['plannedMinutes'] is! int || (t['plannedMinutes'] as int) < 0 || (t['plannedMinutes'] as int) > 600)) throw const FormatException();
        if (t['priority'] != null && ![1, 2, 3].contains(t['priority'])) throw const FormatException();
        if (t['title'] is! String || t['date'] is! String || DateTime.tryParse(t['date'] as String) == null || t['done'] is! bool) throw const FormatException();
      }
      for (final r in newReports) {
        if (r['subject'] is! String || r['date'] is! String || DateTime.tryParse(r['date'] as String) == null) throw const FormatException();
        for (final key in ['minutes','tests','satisfaction','mood','stress']) {
          if (r[key] is! int) throw const FormatException();
        }
        if ((r['minutes'] as int) < 0 || (r['minutes'] as int) > 600 || (r['tests'] as int) < 0 || (r['tests'] as int) > 100 || (r['satisfaction'] as int) < 0 || (r['satisfaction'] as int) > 10 || (r['mood'] as int) < 1 || (r['mood'] as int) > 5 || (r['stress'] as int) < 1 || (r['stress'] as int) > 5) throw const FormatException();
      }
      final confirmed = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(title: const Text('بازیابی اطلاعات؟'), content: Text('این نسخه شامل ${newTasks.length} تکلیف و ${newReports.length} گزارش است. اطلاعات فعلی جایگزین می‌شوند. ابتدا از اطلاعات فعلی پشتیبان بگیرید.'), actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('انصراف')), TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('بازیابی'))]));
      if (confirmed != true || !mounted) return;
      final prefs = await SharedPreferences.getInstance();
      final previousRaw = prefs.getString(storageKey);
      if (previousRaw != null && !await prefs.setString('${storageKey}_before_restore', previousRaw)) throw const FormatException();
      final payload = jsonEncode({'tasks': newTasks, 'reports': newReports, 'studentName': data['studentName']?.toString() ?? '', 'studentGrade': data['studentGrade']?.toString() ?? '', 'studentTrack': data['studentTrack']?.toString() ?? ''});
      if (!await prefs.setString(storageKey, payload)) throw const FormatException();
      if (!mounted) return;
      setState(() {
        tasks = newTasks; reports = newReports;
        studentName = data['studentName']?.toString() ?? ''; studentGrade = data['studentGrade']?.toString() ?? ''; studentTrack = data['studentTrack']?.toString() ?? '';
        nameController.text = studentName; gradeController.text = studentGrade; trackController.text = studentTrack;
        editingTaskIndex = null; editingReportIndex = null; linkedTaskIndex = null; completeLinkedTask = false; reportFormVersion++; planFormVersion++;
      });
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('اطلاعات بازیابی شد.')));
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('بازیابی ناموفق بود؛ نسخه پشتیبان معتبر را کپی کنید.')));
    }
  }
  Widget account() => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    heading('حساب محلی'),
    OutlinedButton.icon(onPressed: exportBackup, icon: const Icon(Icons.backup_outlined), label: const Text('کپی نسخه پشتیبان')),
    OutlinedButton.icon(onPressed: restoreBackup, icon: const Icon(Icons.restore), label: const Text('بازیابی از متن کپی‌شده')),
    const Text('پشتیبان متنی رمزگذاری نشده است؛ آن را فقط در محل خصوصی نگه دارید.'),

    const Text('نسخه آزمایشی ۱۲ • اصلاح گزارش و تحلیل درس'),
    const Card(child: ListTile(title: Text('پروفایل دانش‌آموز'),
      subtitle: Text('مشخصات محلی؛ بدون اتصال به پرونده آنلاین'))),
    TextField(controller: nameController, maxLength: 80, decoration: const InputDecoration(labelText: 'نام و نام خانوادگی')),
    TextField(controller: gradeController, maxLength: 30, decoration: const InputDecoration(labelText: 'پایه تحصیلی')),
    TextField(controller: trackController, maxLength: 40, decoration: const InputDecoration(labelText: 'رشته تحصیلی (در صورت وجود)')),
    FilledButton(onPressed: () async {
      if (nameController.text.trim().isEmpty || gradeController.text.trim().isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('نام و پایه تحصیلی را وارد کنید.')));
        return;
      }
      setState(() { studentName = nameController.text.trim(); studentGrade = gradeController.text.trim(); studentTrack = trackController.text.trim(); });
      await save();
    }, child: const Text('ذخیره مشخصات روی گوشی')),
    Card(child: ListTile(title: const Text('تکالیف ذخیره‌شده'), trailing: Text(tasks.length.toString()))),
    Card(child: ListTile(title: const Text('گزارش‌های ذخیره‌شده'), trailing: Text(reports.length.toString()))),
  ]);
  @override
  Widget build(BuildContext context) => Directionality(textDirection: TextDirection.rtl,
    child: Scaffold(
      appBar: AppBar(title: const Text('Apex360 | ترنم همدلی')),
      body: loadFailed ? Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: [const Text('خواندن اطلاعات ناموفق بود. برای حفاظت از داده‌ها ثبت جدید متوقف شده است.'), OutlinedButton(onPressed: () { setState(() => loadFailed = false); load(); }, child: const Text('تلاش مجدد'))]))) : !ready ? const Center(child: CircularProgressIndicator()) :
        SafeArea(child: ListView(padding: const EdgeInsets.all(18), children: [
          Container(padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: const Color(0xFFE8F0FF), borderRadius: BorderRadius.circular(14)),
            child: const Text('نسخه آفلاین آزمایشی • داده‌ها فقط روی گوشی ذخیره می‌شوند و به ربات یا مشاور ارسال نمی‌شوند. حذف برنامه ممکن است اطلاعات را پاک کند.',
              style: TextStyle(fontSize: 12, height: 1.8))),
          const SizedBox(height: 18),
          if (tab == 0) home(),
          if (tab == 1) plan(),
          if (tab == 2) progress(),
          if (tab == 3) report(),
          if (tab == 4) account(),
        ])),
      bottomNavigationBar: NavigationBar(selectedIndex: tab,
        onDestinationSelected: (v) => setState(() => tab = v),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: 'خانه'),
          NavigationDestination(icon: Icon(Icons.calendar_month_outlined), label: 'برنامه'),
          NavigationDestination(icon: Icon(Icons.bar_chart_outlined), label: 'پیشرفت'),
          NavigationDestination(icon: Icon(Icons.edit_note_outlined), label: 'گزارش'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'حساب'),
        ]),
    ));
}
