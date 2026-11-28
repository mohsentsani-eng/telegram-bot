import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:shamsi_date/shamsi_date.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/encrypted_backup.dart';
import '../theme/app_theme.dart';
import '../theme/apex_components.dart';
import '../services/study_momentum.dart';
import 'apex_dashboard.dart';

/// Offline-only workspace; does not contact the production bot or API.
class ApexDemoScreen extends StatefulWidget {
  const ApexDemoScreen({super.key, this.onThemeChanged});
  final ValueChanged<bool>? onThemeChanged;
  @override
  State<ApexDemoScreen> createState() => _ApexDemoScreenState();
}

class _ApexDemoScreenState extends State<ApexDemoScreen> {
  static const storageKey = 'apex360_offline_v1';
  static const themeKey = 'apex360_dark_mode';
  bool? darkMode;

  Future<void> toggleTheme(bool dark) async {
    setState(() => darkMode = dark);
    if (widget.onThemeChanged case final callback?) {
      callback(dark);
      return;
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      if (await prefs.setBool(themeKey, dark)) return;
    } catch (_) {
      // The current appearance can still be used for this session.
    }
    if (mounted)
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('ذخیره تنظیم نمایش ممکن نشد.')),
      );
  }

  final planScroll = ScrollController();
  final reportScroll = ScrollController();
  final taskController = TextEditingController();
  final subjectController = TextEditingController();
  final topicController = TextEditingController();
  final noteController = TextEditingController();
  int plannedMinutes = 60, priority = 2;
  int? linkedTaskIndex;
  int? editingTaskIndex;
  int planFormVersion = 0;
  bool composingTask = false;
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
    return fa(
      '${j.year}/${j.month.toString().padLeft(2, '0')}/${j.day.toString().padLeft(2, '0')}',
    );
  }

  String get today => DateTime.now().toIso8601String().substring(0, 10);

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final preference = prefs.get(themeKey);
      if (preference is bool) darkMode ??= preference;
      final raw = prefs.getString(storageKey);
      if (raw != null) {
        final data = jsonDecode(raw) as Map<String, dynamic>;
        studentName = data['studentName']?.toString() ?? '';
        studentGrade = data['studentGrade']?.toString() ?? '';
        studentTrack = data['studentTrack']?.toString() ?? '';
        nameController.text = studentName;
        gradeController.text = studentGrade;
        trackController.text = studentTrack;
        tasks = (data['tasks'] as List<dynamic>)
            .map((v) => Map<String, dynamic>.from(v as Map))
            .toList();
        reports = (data['reports'] as List<dynamic>)
            .map((v) => Map<String, dynamic>.from(v as Map))
            .toList();
      }
      if (mounted) setState(() => ready = true);
    } catch (_) {
      if (mounted) setState(() => loadFailed = true);
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'خواندن داده‌ها ممکن نشد. برای حفاظت از اطلاعات، ثبت غیرفعال است.',
            ),
          ),
        );
    }
  }

  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    final success = await prefs.setString(
      storageKey,
      jsonEncode({
        'tasks': tasks,
        'reports': reports,
        'studentName': studentName,
        'studentGrade': studentGrade,
        'studentTrack': studentTrack,
      }),
    );
    if (!success && mounted)
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('ذخیره اطلاعات ناموفق بود.')),
      );
  }

  Future<void> addTask() async {
    final name = taskController.text.trim();
    if (name.isEmpty) return;
    setState(() {
      final task = <String, dynamic>{
        'title': name,
        'topic': topicController.text.trim(),
        'date': selectedDay,
        'plannedMinutes': plannedMinutes,
        'priority': priority,
        'done': false,
      };
      if (editingTaskIndex != null) {
        final i = editingTaskIndex!;
        tasks[i] = {...tasks[i], ...task, 'done': tasks[i]['done']};
      } else {
        tasks.insert(0, task);
      }
      editingTaskIndex = null;
      composingTask = false;
      filterDay = selectedDay;
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
    editingReportIndex = null;
    linkedTaskIndex = null;
    completeLinkedTask = false;
    subjectController.clear();
    noteController.clear();
    minutes = 45;
    tests = 0;
    satisfaction = 7;
    mood = 3;
    stress = 3;
    reportFormVersion++;
  }

  Future<void> addReport() async {
    final name = canonicalSubject(subjectController.text);
    if (name.isEmpty ||
        minutes < 0 ||
        minutes > 600 ||
        tests < 0 ||
        tests > 100) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'نام درس، مدت ۰ تا ۶۰۰ دقیقه و تعداد ۰ تا ۱۰۰ تست را وارد کنید.',
          ),
        ),
      );
      return;
    }
    final linked = linkedTaskIndex == null ? null : tasks[linkedTaskIndex!];
    setState(() {
      if (linked != null && completeLinkedTask) linked['done'] = true;
      final previous =
          editingReportIndex == null ? null : reports[editingReportIndex!];
      final report = <String, dynamic>{
        ...?previous,
        'subject': name,
        'date': previous?['date'] ?? today,
        'linkedTitle': linked?['title'] ?? previous?['linkedTitle'],
        'linkedDate': linked?['date'] ?? previous?['linkedDate'],
        'minutes': minutes,
        'tests': tests,
        'satisfaction': satisfaction,
        'mood': mood,
        'stress': stress,
        'note': noteController.text.trim(),
      };
      if (editingReportIndex == null) {
        reports.insert(0, report);
      } else {
        reports[editingReportIndex!] = report;
      }
      editingReportIndex = null;
    });
    subjectController.clear();
    noteController.clear();
    setState(resetReport);
    await save();
  }

  @override
  void dispose() {
    planScroll.dispose();
    reportScroll.dispose();
    taskController.dispose();
    subjectController.dispose();
    topicController.dispose();
    noteController.dispose();
    nameController.dispose();
    gradeController.dispose();
    trackController.dispose();
    super.dispose();
  }

  Widget heading(String label) => ApexSection(label);

  StudyMomentum get momentum => StudyMomentum([
        for (final row in reports)
          if (DateTime.tryParse(row['date'].toString())
              case final DateTime date)
            (
              day: date,
              minutes: (row['minutes'] as num).toInt(),
              tests: (row['tests'] as num).toInt(),
            ),
      ], DateTime.now());

  void openTodayPlan() => setState(() {
        if (editingTaskIndex == null) selectedDate = DateTime.now();
        filterDay = today;
        tab = 1;
      });

  void reportTask(int index) => setState(() {
        if (editingReportIndex == null) {
          linkedTaskIndex = index;
          completeLinkedTask = false;
          if (subjectController.text.trim().isEmpty) {
            subjectController.text = tasks[index]['title'].toString();
          }
          reportFormVersion++;
        }
        tab = 3;
      });

  Widget home() => ApexDashboard(
        studentName: studentName,
        dateLabel: persianDate(today),
        tasks: tasks.where((task) => task['date'] == today).toList(),
        momentum: momentum,
        onPlan: openTodayPlan,
        onReport: () => setState(() => tab = 3),
        onToggleTask: (task, value) async {
          setState(() => task['done'] = value);
          await save();
        },
      );

  Future<DateTime?> pickJalaliDate() async {
    final initial = Jalali.fromDateTime(selectedDate);
    int year = initial.year, month = initial.month, day = initial.day;
    const months = [
      'فروردین',
      'اردیبهشت',
      'خرداد',
      'تیر',
      'مرداد',
      'شهریور',
      'مهر',
      'آبان',
      'آذر',
      'دی',
      'بهمن',
      'اسفند',
    ];
    const weekdays = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
    return showOfflineDialog<DateTime>(
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, refresh) {
          final first = Jalali(year, month, 1);
          final count = first.monthLength;
          final offset = (first.toDateTime().weekday + 1) % 7;
          void move(int delta) {
            final next = month + delta;
            final y = next == 0
                ? year - 1
                : next == 13
                    ? year + 1
                    : year;
            if (y < 1402 || y > 1415) return;
            refresh(() {
              year = y;
              month = next == 0
                  ? 12
                  : next == 13
                      ? 1
                      : next;
              day = day.clamp(1, Jalali(year, month, 1).monthLength).toInt();
            });
          }

          return AlertDialog(
            title: const Text('انتخاب تاریخ شمسی'),
            scrollable: true,
            content: SizedBox(
              width: 320,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      IconButton(
                        onPressed: () => move(-1),
                        icon: const Icon(Icons.chevron_right),
                        tooltip: 'ماه قبل',
                      ),
                      Flexible(
                        child: Text(
                          '${months[month - 1]} ${fa(year)}',
                          textAlign: TextAlign.center,
                        ),
                      ),
                      IconButton(
                        onPressed: () => move(1),
                        icon: const Icon(Icons.chevron_left),
                        tooltip: 'ماه بعد',
                      ),
                    ],
                  ),
                  Row(
                    children: weekdays
                        .map((w) => Expanded(child: Center(child: Text(w))))
                        .toList(),
                  ),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 7,
                    ),
                    itemCount: offset + count,
                    itemBuilder: (context, i) {
                      final d = i - offset + 1;
                      if (d < 1) return const SizedBox.shrink();
                      return Semantics(
                        selected: day == d,
                        button: true,
                        child: InkWell(
                          onTap: () => refresh(() => day = d),
                          child: Center(
                            child: CircleAvatar(
                              radius: 15,
                              backgroundColor: day == d
                                  ? Theme.of(context).colorScheme.primary
                                  : Colors.transparent,
                              foregroundColor: day == d
                                  ? Theme.of(context).colorScheme.onPrimary
                                  : Theme.of(context).colorScheme.onSurface,
                              child: Text(fa(d)),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('انصراف'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(ctx, DateTime.now()),
                child: const Text('امروز'),
              ),
              FilledButton(
                onPressed: () =>
                    Navigator.pop(ctx, Jalali(year, month, day).toDateTime()),
                child: const Text('تأیید'),
              ),
            ],
          );
        },
      ),
    );
  }

  List<String> get subjectChoices {
    final grade = grades.indexOf(normalizedGrade(studentGrade));
    if (grade < 0) return [];
    if (grade < 6)
      return [
        'فارسی',
        'ریاضی',
        'علوم',
        'قرآن',
        'هدیه‌های آسمان',
        'مطالعات اجتماعی',
      ];
    if (grade < 9)
      return [
        'فارسی',
        'ریاضی',
        'علوم',
        'عربی',
        'زبان انگلیسی',
        'قرآن',
        'پیام‌های آسمان',
        'مطالعات اجتماعی',
        'نگارش',
        'کار و فناوری',
      ];
    return [
      'فارسی',
      'نگارش',
      'دینی',
      'عربی',
      'زبان انگلیسی',
      ...switch (studentTrack) {
        'ریاضی' => [
            'ریاضی',
            'حسابان',
            'هندسه',
            'آمار و احتمال',
            'ریاضیات گسسته',
            'فیزیک',
            'شیمی',
          ],
        'تجربی' => ['ریاضی', 'زیست‌شناسی', 'فیزیک', 'شیمی', 'زمین‌شناسی'],
        'انسانی' => [
            'علوم و فنون ادبی',
            'ریاضی و آمار',
            'جامعه‌شناسی',
            'تاریخ',
            'جغرافیا',
            'اقتصاد',
            'منطق',
            'فلسفه',
            'روان‌شناسی',
          ],
        _ => <String>[],
      },
    ];
  }

  bool allSubjects = false;
  int get quickSubjectLimit => allSubjects ? subjectChoices.length : 5;

  Widget subjectSuggestions(TextEditingController controller) => Wrap(
        spacing: 8,
        children: [
          for (final name in (subjectChoices.isEmpty
                  ? ['ریاضی', 'فارسی', 'علوم']
                  : subjectChoices)
              .take(quickSubjectLimit))
            ActionChip(
              avatar: const Icon(Icons.book_outlined, size: 16),
              label: Text(name),
              onPressed: () => setState(() => controller.text = name),
            ),
          if (subjectChoices.length > 5)
            TextButton(
              onPressed: () => setState(() => allSubjects = !allSubjects),
              child: Text(allSubjects ? 'درس‌های کمتر' : 'همهٔ درس‌ها'),
            ),
        ],
      );

  Widget weekCalendar() {
    final now = DateTime.now();
    const weekdays = [
      'شنبه',
      'یکشنبه',
      'دوشنبه',
      'سه‌شنبه',
      'چهارشنبه',
      'پنجشنبه',
      'جمعه',
    ];
    final colors = offlineTheme.colorScheme;
    return LayoutBuilder(
        builder: (context, constraints) => SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SizedBox(
                width: constraints.maxWidth < 336 ? 336 : constraints.maxWidth,
                child: Row(
                  children: [
                    for (final (index, name) in weekdays.indexed)
                      Expanded(
                        child: Builder(
                          builder: (context) {
                            final day = DateTime(
                              now.year,
                              now.month,
                              now.day - (now.weekday + 1) % 7 + index,
                            );
                            final key = day.toIso8601String().substring(0, 10);
                            final selected = filterDay == key;
                            final entries =
                                tasks.where((task) => task['date'] == key);
                            final done = entries
                                .where((task) => task['done'] == true)
                                .length;
                            return Semantics(
                              button: true,
                              selected: selected,
                              onTap: () => setState(() => filterDay = key),
                              label:
                                  '$name ${persianDate(key)}، ${fa(done)} از ${fa(entries.length)} تکلیف انجام شد',
                              child: Material(
                                color: selected
                                    ? colors.primaryContainer
                                    : colors.surface,
                                borderRadius: BorderRadius.circular(16),
                                child: InkWell(
                                  borderRadius: BorderRadius.circular(16),
                                  onTap: () => setState(() => filterDay = key),
                                  child: ExcludeSemantics(
                                    child: Padding(
                                      padding: const EdgeInsets.symmetric(
                                        vertical: 8,
                                        horizontal: 2,
                                      ),
                                      child: Column(
                                        children: [
                                          Text([
                                            'ش',
                                            'ی',
                                            'د',
                                            'س',
                                            'چ',
                                            'پ',
                                            'ج'
                                          ][index]),
                                          FittedBox(
                                            child: Text(fa(
                                                Jalali.fromDateTime(day).day)),
                                          ),
                                          Icon(
                                            entries.isEmpty
                                                ? Icons.remove
                                                : done == entries.length
                                                    ? Icons.check_circle
                                                    : Icons.circle,
                                            size: 13,
                                            color: colors.primary,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                  ],
                ))));
  }

  Widget planComposer() => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                editingTaskIndex == null ? 'یک تکلیف تازه' : 'ویرایش تکلیف',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              subjectSuggestions(taskController),
              TextField(
                controller: taskController,
                maxLength: 100,
                decoration: const InputDecoration(
                  labelText: 'درس یا تکلیف',
                  counterText: '',
                ),
              ),
              const SizedBox(height: 8),
              MinuteChoices(
                selected: plannedMinutes,
                onSelect: (value) => setState(() {
                  plannedMinutes = value;
                  planFormVersion++;
                }),
              ),
              ExpansionTile(
                title: Text(
                  'زمان دقیق، مبحث و اولویت · ${fa(plannedMinutes)} دقیقه',
                ),
                children: [
                  TextField(
                    controller: topicController,
                    maxLength: 100,
                    decoration: const InputDecoration(
                      labelText: 'مبحث یا نوع فعالیت',
                    ),
                  ),
                  TextFormField(
                    key: ValueKey(planFormVersion),
                    initialValue: plannedMinutes.toString(),
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'زمان دقیق (دقیقه)',
                    ),
                    onChanged: (value) {
                      final n = int.tryParse(latinDigits(value));
                      if (n != null && n >= 0 && n <= 600)
                        setState(() => plannedMinutes = n);
                    },
                  ),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final (i, label) in ['زیاد', 'متوسط', 'کم'].indexed)
                        ChoiceChip(
                          label: Text('اولویت $label'),
                          selected: priority == i + 1,
                          onSelected: (_) => setState(() => priority = i + 1),
                        ),
                    ],
                  ),
                ],
              ),
              OutlinedButton.icon(
                onPressed: () async {
                  final picked = await pickJalaliDate();
                  if (picked != null && mounted)
                    setState(() => selectedDate = picked);
                },
                icon: const Icon(Icons.event),
                label: Text('تاریخ برنامه · ${persianDate(selectedDay)}'),
              ),
              FilledButton(
                onPressed: addTask,
                child: Text(
                  editingTaskIndex == null
                      ? 'افزودن به برنامه'
                      : 'ذخیره تغییرات',
                ),
              ),
              TextButton(
                onPressed: () => setState(() {
                  composingTask = false;
                  editingTaskIndex = null;
                  taskController.clear();
                  topicController.clear();
                  planFormVersion++;
                }),
                child: const Text('انصراف'),
              ),
            ],
          ),
        ),
      );

  Widget plan() => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const ApexSection(
            'برنامه شخصی روزانه',
            detail: 'یک روز را انتخاب کن و قدم‌های همان روز را ببین.',
          ),
          weekCalendar(),
          Wrap(
            spacing: 8,
            children: [
              ChoiceChip(
                label: const Text('همه'),
                selected: filterDay == null,
                onSelected: (_) => setState(() => filterDay = null),
              ),
              ChoiceChip(
                label: const Text('نمای امروز'),
                selected: filterDay == today,
                onSelected: (_) => openTodayPlan(),
              ),
              ActionChip(
                avatar: const Icon(Icons.calendar_month_outlined),
                label: const Text('تاریخ دیگر'),
                onPressed: () async {
                  final picked = await pickJalaliDate();
                  if (picked != null && mounted)
                    setState(
                      () =>
                          filterDay = picked.toIso8601String().substring(0, 10),
                    );
                },
              ),
            ],
          ),
          if (composingTask)
            planComposer()
          else
            FilledButton.icon(
              icon: const Icon(Icons.add),
              label: const Text('تکلیف تازه'),
              onPressed: () => setState(() {
                selectedDate =
                    DateTime.tryParse(filterDay ?? '') ?? DateTime.now();
                plannedMinutes = 60;
                priority = 2;
                composingTask = true;
              }),
            ),
          ApexSection(
            'تکلیف‌ها',
            detail: filterDay == null ? null : persianDate(filterDay!),
          ),
          if (!tasks.any((t) => filterDay == null || t['date'] == filterDay))
            const Text('برای این بازه تکلیفی ثبت نشده است.'),
          ...tasks
              .asMap()
              .entries
              .where(
                (entry) =>
                    filterDay == null || entry.value['date'] == filterDay,
              )
              .map(
                (entry) => Card(
                  child: Column(
                    children: [
                      CheckboxListTile(
                        title: Text(entry.value['title'] as String),
                        secondary: SubjectMark(entry.value['title'].toString()),
                        subtitle: Text(
                          persianDate(entry.value['date'].toString()) +
                              ' • ' +
                              (entry.value['topic'] ?? '').toString() +
                              ' • ' +
                              (entry.value['plannedMinutes'] ?? 'نامشخص')
                                  .toString() +
                              ' دقیقه',
                        ),
                        value: entry.value['done'] == true,
                        onChanged: (value) async {
                          setState(
                              () => tasks[entry.key]['done'] = value ?? false);
                          await save();
                        },
                      ),
                      Wrap(
                        alignment: WrapAlignment.end,
                        children: [
                          TextButton.icon(
                            icon: const Icon(Icons.edit_note),
                            label: const Text('ثبت مطالعه'),
                            onPressed: () => reportTask(entry.key),
                          ),
                          TextButton.icon(
                            icon: const Icon(Icons.edit_outlined),
                            label: const Text('ویرایش'),
                            onPressed: () {
                              setState(() {
                                composingTask = true;
                                editingTaskIndex = entry.key;
                                taskController.text =
                                    entry.value['title'].toString();
                                topicController.text =
                                    (entry.value['topic'] ?? '').toString();
                                selectedDate = DateTime.tryParse(
                                      entry.value['date'].toString(),
                                    ) ??
                                    DateTime.now();
                                plannedMinutes =
                                    (entry.value['plannedMinutes'] as num?)
                                            ?.toInt() ??
                                        60;
                                priority = (entry.value['priority'] as num?)
                                        ?.toInt() ??
                                    2;
                                planFormVersion++;
                              });
                              planScroll.jumpTo(0);
                            },
                          ),
                          TextButton.icon(
                            icon: const Icon(Icons.delete_outline),
                            label: const Text('حذف'),
                            onPressed: () async {
                              final confirmed = await showOfflineDialog<bool>(
                                builder: (ctx) => AlertDialog(
                                  title: const Text('حذف تکلیف؟'),
                                  content: const Text(
                                    'گزارش‌های مطالعه حذف نمی‌شوند.',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.pop(ctx, false),
                                      child: const Text('انصراف'),
                                    ),
                                    TextButton(
                                      onPressed: () => Navigator.pop(ctx, true),
                                      child: const Text('حذف'),
                                    ),
                                  ],
                                ),
                              );
                              if (confirmed != true || !mounted) return;
                              setState(() {
                                tasks.removeAt(entry.key);
                                editingTaskIndex = null;
                                composingTask = false;
                                linkedTaskIndex = null;
                                completeLinkedTask = false;
                                reportFormVersion++;
                              });
                              await save();
                            },
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
        ],
      );
  Widget report() => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const ApexSection(
            'ثبت گزارش روزانه',
            detail: 'درس و زمان مطالعه را انتخاب کن.',
          ),
          subjectSuggestions(subjectController),
          TextField(
            controller: subjectController,
            maxLength: 80,
            decoration: const InputDecoration(labelText: 'نام درس'),
          ),
          MinuteChoices(
            selected: minutes,
            onSelect: (value) => setState(() {
              minutes = value;
              reportFormVersion++;
            }),
          ),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  key: ValueKey('minutes-$reportFormVersion'),
                  initialValue: minutes.toString(),
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'دقیقه مطالعه'),
                  onChanged: (value) =>
                      minutes = int.tryParse(latinDigits(value)) ?? -1,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextFormField(
                  key: ValueKey('tests-$reportFormVersion'),
                  initialValue: tests.toString(),
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'تعداد تست'),
                  onChanged: (value) =>
                      tests = int.tryParse(latinDigits(value)) ?? -1,
                ),
              ),
            ],
          ),
          if (tasks.isNotEmpty)
            ExpansionTile(
              key: ValueKey('link-$reportFormVersion'),
              title: const Text('تکلیف مربوط به این مطالعه'),
              initiallyExpanded: linkedTaskIndex != null,
              children: [
                if (tasks.isNotEmpty)
                  DropdownButtonFormField<int>(
                    isExpanded: true,
                    key: ValueKey(reportFormVersion),
                    initialValue: linkedTaskIndex,
                    decoration: const InputDecoration(
                      labelText: 'اتصال گزارش به تکلیف برنامه',
                    ),
                    items: [
                      const DropdownMenuItem<int>(
                        value: -1,
                        child: Text('بدون اتصال'),
                      ),
                      ...tasks.asMap().entries.map(
                            (e) => DropdownMenuItem<int>(
                              value: e.key,
                              child: Text(
                                e.value['title'].toString() +
                                    ' • ' +
                                    persianDate(e.value['date'].toString()),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ),
                    ],
                    onChanged: (v) => setState(() {
                      linkedTaskIndex = v == -1 ? null : v;
                      completeLinkedTask = false;
                      if (linkedTaskIndex != null)
                        subjectController.text =
                            tasks[linkedTaskIndex!]['title'].toString();
                    }),
                  ),
                if (linkedTaskIndex != null)
                  CheckboxListTile(
                    title: const Text('این تکلیف را کامل انجام دادم'),
                    value: completeLinkedTask,
                    onChanged: (v) =>
                        setState(() => completeLinkedTask = v ?? false),
                  ),
              ],
            ),
          ExpansionTile(
            title: const Text('جزئیات گزارش (اختیاری)'),
            initiallyExpanded: editingReportIndex != null,
            key: ValueKey('details-$reportFormVersion'),
            children: [
              Text('رضایت از عملکرد: ' + satisfaction.toString() + ' از ۱۰'),
              Slider(
                value: satisfaction.toDouble(),
                min: 0,
                max: 10,
                divisions: 10,
                onChanged: (value) =>
                    setState(() => satisfaction = value.round()),
              ),
              Text('خلق امروز: ' + mood.toString() + ' از ۵'),
              Slider(
                value: mood.toDouble(),
                min: 1,
                max: 5,
                divisions: 4,
                onChanged: (value) => setState(() => mood = value.round()),
              ),
              Text('استرس امروز: ' + stress.toString() + ' از ۵'),
              Slider(
                value: stress.toDouble(),
                min: 1,
                max: 5,
                divisions: 4,
                onChanged: (value) => setState(() => stress = value.round()),
              ),
              TextField(
                controller: noteController,
                maxLines: 3,
                maxLength: 400,
                decoration: const InputDecoration(
                  labelText: 'کارهای انجام‌نشده و علت آن / توضیحات',
                ),
              ),
            ],
          ),
          FilledButton(
            onPressed: addReport,
            child: Text(
              editingReportIndex == null
                  ? 'ذخیره گزارش روی گوشی'
                  : 'ذخیره اصلاحات گزارش',
            ),
          ),
          if (editingReportIndex != null)
            TextButton(
              onPressed: () => setState(resetReport),
              child: const Text('انصراف از ویرایش گزارش'),
            ),
          const SizedBox(height: 16),
          heading('گزارش‌های ثبت‌شده'),
          ...reports.asMap().entries.take(30).map((entry) {
            final r = entry.value;
            return Card(
              child: ListTile(
                title: Text(
                  r['subject'].toString() +
                      ' • ' +
                      r['minutes'].toString() +
                      ' دقیقه • ' +
                      r['tests'].toString() +
                      ' تست',
                ),
                subtitle: Text(
                  persianDate(r['date'].toString()) +
                      ' | رضایت ' +
                      r['satisfaction'].toString() +
                      '/۱۰ | خلق ' +
                      r['mood'].toString() +
                      '/۵ | استرس ' +
                      r['stress'].toString() +
                      '/۵',
                ),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.delete_outline),
                      tooltip: 'حذف گزارش',
                      onPressed: () async {
                        final ok = await showOfflineDialog<bool>(
                          builder: (ctx) => AlertDialog(
                            title: const Text('حذف گزارش؟'),
                            content: const Text(
                              'این گزارش حذف می‌شود؛ وضعیت تکلیف تغییر نمی‌کند.',
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(ctx, false),
                                child: const Text('انصراف'),
                              ),
                              TextButton(
                                onPressed: () => Navigator.pop(ctx, true),
                                child: const Text('حذف'),
                              ),
                            ],
                          ),
                        );
                        if (ok != true || !mounted) return;
                        setState(() {
                          reports.removeAt(entry.key);
                          resetReport();
                        });
                        await save();
                      },
                    ),
                    IconButton(
                      icon: const Icon(Icons.edit_outlined),
                      tooltip: 'ویرایش گزارش',
                      onPressed: () {
                        setState(() {
                          editingReportIndex = entry.key;
                          subjectController.text = r['subject'].toString();
                          noteController.text = (r['note'] ?? '').toString();
                          minutes = (r['minutes'] as num).toInt();
                          tests = (r['tests'] as num).toInt();
                          satisfaction = (r['satisfaction'] as num).toInt();
                          mood = (r['mood'] as num).toInt();
                          stress = (r['stress'] as num).toInt();
                          linkedTaskIndex = null;
                          completeLinkedTask = false;
                          reportFormVersion++;
                        });
                        reportScroll.jumpTo(0);
                      },
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      );
  Widget progress() {
    final now = DateTime.now();
    final days = List.generate(7, (i) {
      final date = DateTime(
        now.year,
        now.month,
        now.day - 6 + i,
      ).toIso8601String().substring(0, 10);
      final sum = reports
          .where((r) => r['date'] == date)
          .fold<int>(0, (n, r) => n + (r['minutes'] as int));
      return (date: date, sum: sum);
    });
    final total = days.fold<int>(0, (n, d) => n + d.sum);
    final recentDates = days.map((d) => d.date).toSet();
    final recentTasks =
        tasks.where((t) => recentDates.contains(t['date'])).toList();
    final completed = recentTasks.where((t) => t['done'] == true).length;
    final planned = recentTasks.fold<int>(
      0,
      (n, t) => n + ((t['plannedMinutes'] as num?)?.toInt() ?? 0),
    );
    final testsByDate = <String, int>{};
    final bySubject = <String, int>{};
    final testsBySubject = <String, int>{};
    for (final r in reports.where((r) => recentDates.contains(r['date']))) {
      final date = r['date'].toString();
      final testCount = (r['tests'] as num).toInt();
      testsByDate.update(
        date,
        (count) => count + testCount,
        ifAbsent: () => testCount,
      );
      final name = canonicalSubject(r['subject'].toString());
      bySubject.update(
        name,
        (v) => v + (r['minutes'] as int),
        ifAbsent: () => r['minutes'] as int,
      );
      testsBySubject.update(
        name,
        (v) => v + (r['tests'] as int),
        ifAbsent: () => r['tests'] as int,
      );
    }
    final percent = recentTasks.isEmpty
        ? 0
        : (100 * completed / recentTasks.length).round();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const ApexSection(
          'پیشرفت هفت روز گذشته',
          detail: 'زمان و تمرین‌های خودت را دنبال کن.',
        ),
        ApexWeekChart(
          title: 'زمان مطالعه',
          unit: 'دقیقه',
          days: [
            for (final day in days)
              (label: persianDate(day.date).substring(5), value: day.sum),
          ],
        ),
        ApexWeekChart(
          title: 'تعداد تست',
          unit: 'تست',
          days: [
            for (final day in days)
              (
                label: persianDate(day.date).substring(5),
                value: testsByDate[day.date] ?? 0,
              ),
          ],
        ),
        StudyAchievements(momentum: momentum),
        Card(
          child: ListTile(
            title: const Text('مجموع مطالعه هفتگی'),
            trailing: Text((total / 60).toStringAsFixed(1) + ' ساعت'),
          ),
        ),
        Card(
          child: ListTile(
            title: const Text('پایبندی به برنامه هفتگی'),
            subtitle: Text(
              recentTasks.isEmpty
                  ? 'هنوز برنامه‌ای ثبت نشده'
                  : completed.toString() +
                      ' تکلیف از ' +
                      recentTasks.length.toString(),
            ),
            trailing: ProgressRing(
              value: percent / 100,
              label: recentTasks.isEmpty ? '—' : '${fa(percent)}٪',
            ),
          ),
        ),
        Card(
          child: ListTile(
            title: const Text('زمان برنامه‌ریزی‌شده هفتگی'),
            trailing: Text(planned.toString() + ' دقیقه'),
          ),
        ),
        heading('کیفیت عملکرد و حال عمومی'),
        if (reports.where((r) => recentDates.contains(r['date'])).isEmpty)
          const Text('برای مشاهده روند، گزارش مطالعه ثبت کنید.'),
        ...['satisfaction', 'mood', 'stress'].map((key) {
          final values = reports
              .where((r) => recentDates.contains(r['date']) && r[key] is num)
              .map((r) => (r[key] as num).toDouble())
              .toList();
          final limit = key == 'satisfaction' ? 10 : 5;
          final label = key == 'satisfaction'
              ? 'رضایت از عملکرد'
              : key == 'mood'
                  ? 'خلق خودگزارش‌شده'
                  : 'استرس خودگزارش‌شده';
          final average = values.isEmpty
              ? 0.0
              : values.reduce((a, b) => a + b) / values.length;
          return Card(
            child: ListTile(
              title: Text(label),
              subtitle: values.isEmpty
                  ? const Text('داده کافی نیست')
                  : LinearProgressIndicator(
                      value: (average / limit).clamp(0.0, 1.0).toDouble(),
                    ),
              trailing: Text(
                values.isEmpty
                    ? '—'
                    : '${average.toStringAsFixed(1)} از $limit',
              ),
            ),
          );
        }),
        const Text(
          'این شاخص‌ها میانگین گزارش‌های شخصی هستند و تشخیص روان‌شناختی محسوب نمی‌شوند.',
        ),
        heading('عملکرد به تفکیک درس'),
        if (bySubject.isEmpty)
          const Text('هنوز گزارشی در این هفته ثبت نشده است.'),
        ...bySubject.entries.map(
          (e) => Card(
            child: ListTile(
              leading: SubjectMark(e.key),
              title: Text(e.key),
              subtitle: Text('${testsBySubject[e.key]} تست'),
              trailing: Text('${e.value} دقیقه'),
            ),
          ),
        ),
        heading('پیشنهاد مطالعاتی'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              total == 0
                  ? 'برای شروع، یک فعالیت کوتاه و قابل انجام برنامه‌ریزی کنید.'
                  : recentTasks.isEmpty
                      ? 'برای مطالعه بعدی، تکلیف مشخصی در برنامه ثبت کنید تا بتوانید میزان پایبندی را بسنجید.'
                      : completed < recentTasks.length
                          ? 'تکالیف باقی‌مانده را بررسی کنید و برای هرکدام زمان واقع‌بینانه تعیین کنید.'
                          : 'تکالیف ثبت‌شده انجام شده‌اند؛ مرور و تمرین بازیابی را در برنامه بعدی بگنجانید.',
            ),
          ),
        ),
        const Text(
          'پیشنهاد خودکار بر اساس گزارش محلی؛ جایگزین نظر مشاور نیست.',
        ),
      ],
    );
  }

  Future<void> recoverPreviousBackup() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('${storageKey}_before_restore');
    if (!mounted) return;
    if (raw == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('نسخه قبلی برای بازیابی وجود ندارد.')),
      );
      return;
    }
    try {
      final data = jsonDecode(raw) as Map<String, dynamic>;
      await restoreBackup(
        suppliedRaw: jsonEncode({...data, 'format': 'apex360-backup-v1'}),
      );
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('خواندن نسخه قبلی ناموفق بود.')),
        );
    }
  }

  Future<String?> backupPassword(bool creating) async {
    String password = '', confirmation = '';
    return showOfflineDialog<String>(
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, refresh) => AlertDialog(
          title: Text(creating ? 'رمز نسخه پشتیبان' : 'رمز بازیابی'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                obscureText: true,
                autocorrect: false,
                enableSuggestions: false,
                decoration: const InputDecoration(
                  labelText: 'رمز (حداقل ۱۲ نویسه)',
                ),
                onChanged: (v) => refresh(() => password = v),
              ),
              if (creating)
                TextField(
                  obscureText: true,
                  autocorrect: false,
                  enableSuggestions: false,
                  decoration: const InputDecoration(labelText: 'تکرار رمز'),
                  onChanged: (v) => refresh(() => confirmation = v),
                ),
              if (creating)
                const Text('رمز را در محل امن نگه دارید؛ قابل بازیابی نیست.'),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('انصراف'),
            ),
            FilledButton(
              onPressed:
                  password.length < 12 || (creating && password != confirmation)
                      ? null
                      : () => Navigator.pop(ctx, password),
              child: const Text('ادامه'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> encryptedBackup() async {
    final password = await backupPassword(true);
    if (password == null || !mounted) return;
    try {
      final payload = jsonEncode({
        'format': 'apex360-backup-v1',
        'tasks': tasks,
        'reports': reports,
        'studentName': studentName,
        'studentGrade': studentGrade,
        'studentTrack': studentTrack,
      });
      final bytes = await EncryptedBackup.encode(payload, password);
      if (!mounted) return;
      final result = await FilePicker.platform.saveFile(
        dialogTitle: 'ذخیره پشتیبان رمزگذاری‌شده',
        fileName: 'apex360-$today.apexbackup',
        bytes: bytes,
      );
      if (result != null && mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('پشتیبان ذخیره شد. رمز را در محل امن نگه دارید.'),
          ),
        );
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('ذخیره پشتیبان ناموفق بود.')),
        );
    }
  }

  Future<void> importEncryptedBackup() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        withData: true,
        allowMultiple: false,
      );
      if (result == null || !mounted) return;
      final bytes = result.files.single.bytes;
      if (bytes == null || bytes.length > 8000000)
        throw const FormatException();
      final password = await backupPassword(false);
      if (password == null || !mounted) return;
      final plain = await EncryptedBackup.decode(bytes, password);
      if (mounted) await restoreBackup(suppliedRaw: plain);
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('رمز نادرست یا فایل پشتیبان نامعتبر است.'),
          ),
        );
    }
  }

  Future<void> exportBackup() async {
    final confirmed = await showOfflineDialog<bool>(
      builder: (ctx) => AlertDialog(
        title: const Text('پشتیبان‌گیری از اطلاعات شخصی'),
        content: const Text(
          'این نسخه شامل نام، برنامه و گزارش‌های شخصی است و رمزگذاری نشده است. فقط در محل خصوصی ذخیره کنید و برای دیگران نفرستید.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('انصراف'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('کپی پشتیبان'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    final payload = jsonEncode({
      'format': 'apex360-backup-v1',
      'tasks': tasks,
      'reports': reports,
      'studentName': studentName,
      'studentGrade': studentGrade,
      'studentTrack': studentTrack,
    });
    await Clipboard.setData(ClipboardData(text: payload));
    if (mounted)
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'نسخه پشتیبان کپی شد. آن را در محلی خصوصی ذخیره کنید؛ شامل اطلاعات شخصی است.',
          ),
        ),
      );
  }

  Future<void> restoreBackup({String? suppliedRaw}) async {
    final clip = suppliedRaw == null
        ? await Clipboard.getData(Clipboard.kTextPlain)
        : null;
    if (!mounted) return;
    try {
      final raw = suppliedRaw ?? clip?.text ?? '';
      if (raw.length > 5000000) throw const FormatException();
      final data = jsonDecode(raw) as Map<String, dynamic>;
      if (data['format'] != 'apex360-backup-v1') throw const FormatException();
      for (final key in ['studentName', 'studentGrade', 'studentTrack']) {
        if (data[key] != null &&
            (data[key] is! String || (data[key] as String).length > 100))
          throw const FormatException();
      }
      if (data['tasks'] is! List ||
          data['reports'] is! List ||
          (data['tasks'] as List).length > 20000 ||
          (data['reports'] as List).length > 20000)
        throw const FormatException();
      final newTasks = (data['tasks'] as List)
          .map((v) => Map<String, dynamic>.from(v as Map))
          .toList();
      final newReports = (data['reports'] as List)
          .map((v) => Map<String, dynamic>.from(v as Map))
          .toList();
      for (final t in newTasks) {
        if (t['plannedMinutes'] != null &&
            (t['plannedMinutes'] is! int ||
                (t['plannedMinutes'] as int) < 0 ||
                (t['plannedMinutes'] as int) > 600))
          throw const FormatException();
        if (t['priority'] != null && ![1, 2, 3].contains(t['priority']))
          throw const FormatException();
        if (t['title'] is! String ||
            t['date'] is! String ||
            DateTime.tryParse(t['date'] as String) == null ||
            t['done'] is! bool) throw const FormatException();
      }
      for (final r in newReports) {
        if (r['subject'] is! String ||
            r['date'] is! String ||
            DateTime.tryParse(r['date'] as String) == null)
          throw const FormatException();
        for (final key in [
          'minutes',
          'tests',
          'satisfaction',
          'mood',
          'stress',
        ]) {
          if (r[key] is! int) throw const FormatException();
        }
        if ((r['minutes'] as int) < 0 ||
            (r['minutes'] as int) > 600 ||
            (r['tests'] as int) < 0 ||
            (r['tests'] as int) > 100 ||
            (r['satisfaction'] as int) < 0 ||
            (r['satisfaction'] as int) > 10 ||
            (r['mood'] as int) < 1 ||
            (r['mood'] as int) > 5 ||
            (r['stress'] as int) < 1 ||
            (r['stress'] as int) > 5) throw const FormatException();
      }
      final confirmed = await showOfflineDialog<bool>(
        builder: (ctx) => AlertDialog(
          title: const Text('بازیابی اطلاعات؟'),
          content: Text(
            'این نسخه شامل ${newTasks.length} تکلیف و ${newReports.length} گزارش است. اطلاعات فعلی جایگزین می‌شوند. ابتدا از اطلاعات فعلی پشتیبان بگیرید.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('انصراف'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('بازیابی'),
            ),
          ],
        ),
      );
      if (confirmed != true || !mounted) return;
      final prefs = await SharedPreferences.getInstance();
      final previousRaw = prefs.getString(storageKey);
      if (previousRaw != null &&
          !await prefs.setString('${storageKey}_before_restore', previousRaw))
        throw const FormatException();
      final payload = jsonEncode({
        'tasks': newTasks,
        'reports': newReports,
        'studentName': data['studentName']?.toString() ?? '',
        'studentGrade': data['studentGrade']?.toString() ?? '',
        'studentTrack': data['studentTrack']?.toString() ?? '',
      });
      if (!await prefs.setString(storageKey, payload))
        throw const FormatException();
      if (!mounted) return;
      setState(() {
        resetReport();
        taskController.clear();
        topicController.clear();
        filterDay = null;
        tasks = newTasks;
        reports = newReports;
        studentName = data['studentName']?.toString() ?? '';
        studentGrade = data['studentGrade']?.toString() ?? '';
        studentTrack = data['studentTrack']?.toString() ?? '';
        nameController.text = studentName;
        gradeController.text = studentGrade;
        trackController.text = studentTrack;
        editingTaskIndex = null;
        editingReportIndex = null;
        linkedTaskIndex = null;
        completeLinkedTask = false;
        reportFormVersion++;
        planFormVersion++;
      });
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('اطلاعات بازیابی شد.')));
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'بازیابی ناموفق بود؛ نسخه پشتیبان معتبر را کپی کنید.',
            ),
          ),
        );
    }
  }

  static const grades = [
    'اول',
    'دوم',
    'سوم',
    'چهارم',
    'پنجم',
    'ششم',
    'هفتم',
    'هشتم',
    'نهم',
    'دهم',
    'یازدهم',
    'دوازدهم',
  ];
  static const tracks = [
    'ریاضی',
    'تجربی',
    'انسانی',
    'معارف',
    'فنی‌وحرفه‌ای',
    'کاردانش',
    'سایر',
  ];
  String normalizedGrade(String value) {
    var v = value.trim();
    for (var i = 0; i < 10; i++) {
      v = v.replaceAll('۰۱۲۳۴۵۶۷۸۹'[i], '$i');
    }
    final n = int.tryParse(v);
    return n != null && n >= 1 && n <= 12 ? grades[n - 1] : v;
  }

  bool get profileComplete =>
      studentName.trim().isNotEmpty &&
      grades.contains(normalizedGrade(studentGrade)) &&
      (!grades.skip(9).contains(normalizedGrade(studentGrade)) ||
          tracks.contains(studentTrack));
  Widget account() => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const ApexSection(
            'حساب محلی',
            detail: 'برنامه و گزارش‌های شخصی روی همین گوشی ذخیره می‌شوند.',
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.person_rounded),
              title: Text(profileComplete ? studentName : 'پروفایل دانش‌آموز'),
              subtitle: Text(
                profileComplete
                    ? [
                        studentGrade,
                        studentTrack,
                      ].where((value) => value.isNotEmpty).join(' · ')
                    : 'مشخصات محلی این گوشی',
              ),
            ),
          ),
          Card(
            child: ExpansionTile(
              title: const Text('ویرایش پروفایل'),
              initiallyExpanded: !profileComplete,
              childrenPadding: const EdgeInsets.all(12),
              children: [
                TextField(
                  controller: nameController,
                  maxLength: 80,
                  decoration: const InputDecoration(
                    labelText: 'نام و نام خانوادگی',
                  ),
                ),
                DropdownButtonFormField<String>(
                  key: ValueKey('grade-$studentGrade'),
                  initialValue:
                      grades.contains(normalizedGrade(gradeController.text))
                          ? normalizedGrade(gradeController.text)
                          : null,
                  decoration: const InputDecoration(labelText: 'پایه تحصیلی'),
                  items: grades
                      .map((v) => DropdownMenuItem(value: v, child: Text(v)))
                      .toList(),
                  onChanged: (v) => setState(() {
                    gradeController.text = v ?? '';
                    if (!grades.skip(9).contains(v)) trackController.clear();
                  }),
                ),
                if (grades
                    .skip(9)
                    .contains(normalizedGrade(gradeController.text)))
                  DropdownButtonFormField<String>(
                    key: ValueKey('track-$studentTrack'),
                    initialValue: tracks.contains(trackController.text)
                        ? trackController.text
                        : null,
                    decoration: const InputDecoration(labelText: 'رشته تحصیلی'),
                    items: tracks
                        .map((v) => DropdownMenuItem(value: v, child: Text(v)))
                        .toList(),
                    onChanged: (v) =>
                        setState(() => trackController.text = v ?? ''),
                  ),
                FilledButton(
                  onPressed: () async {
                    if (nameController.text.trim().isEmpty ||
                        !grades
                            .contains(normalizedGrade(gradeController.text)) ||
                        (grades.skip(9).contains(
                                normalizedGrade(gradeController.text)) &&
                            !tracks.contains(trackController.text))) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('نام و پایه تحصیلی را وارد کنید.'),
                        ),
                      );
                      return;
                    }
                    setState(() {
                      studentName = nameController.text.trim();
                      studentGrade = normalizedGrade(gradeController.text);
                      studentTrack = grades.skip(9).contains(studentGrade)
                          ? trackController.text.trim()
                          : '';
                      tab = 0;
                    });
                    await save();
                  },
                  child: const Text('ذخیره مشخصات روی گوشی'),
                ),
              ],
            ),
          ),
          Card(
            child: ExpansionTile(
              leading: const Icon(Icons.shield_outlined),
              title: const Text('پشتیبان‌گیری و بازیابی'),
              childrenPadding: const EdgeInsets.all(12),
              children: [
                FilledButton.icon(
                  onPressed: encryptedBackup,
                  icon: const Icon(Icons.lock_outline),
                  label: const Text('ذخیره فایل پشتیبان رمزدار'),
                ),
                OutlinedButton.icon(
                  onPressed: importEncryptedBackup,
                  icon: const Icon(Icons.folder_open),
                  label: const Text('بازیابی فایل رمزدار'),
                ),
                const Text(
                  'رمز پشتیبان را فراموش نکنید؛ بدون آن بازیابی ممکن نیست.',
                ),
                OutlinedButton.icon(
                  onPressed: exportBackup,
                  icon: const Icon(Icons.backup_outlined),
                  label: const Text('کپی نسخه پشتیبان'),
                ),
                OutlinedButton.icon(
                  onPressed: restoreBackup,
                  icon: const Icon(Icons.restore),
                  label: const Text('بازیابی از متن کپی‌شده'),
                ),
                TextButton.icon(
                  onPressed: recoverPreviousBackup,
                  icon: const Icon(Icons.undo),
                  label: const Text('بازگردانی اطلاعات قبل از آخرین بازیابی'),
                ),
                const Text(
                  'پشتیبان متنی رمزگذاری نشده است؛ آن را فقط در محل خصوصی نگه دارید.',
                ),
              ],
            ),
          ),
          Card(
            child: ListTile(
              title: const Text('تکالیف ذخیره‌شده'),
              trailing: Text(tasks.length.toString()),
            ),
          ),
          Card(
            child: ListTile(
              title: const Text('گزارش‌های ذخیره‌شده'),
              trailing: Text(reports.length.toString()),
            ),
          ),
        ],
      );
  bool get isDark =>
      darkMode ??
      (widget.onThemeChanged != null
          ? Theme.of(context).brightness == Brightness.dark
          : MediaQuery.platformBrightnessOf(context) == Brightness.dark);

  ThemeData get offlineTheme =>
      AppTheme.build(isDark ? Brightness.dark : Brightness.light);

  Future<T?> showOfflineDialog<T>({required WidgetBuilder builder}) {
    final theme = offlineTheme;
    return showDialog<T>(
      context: context,
      builder: (dialogContext) => Theme(
        data: theme,
        child: Directionality(
          textDirection: TextDirection.rtl,
          child: Builder(builder: builder),
        ),
      ),
    );
  }

  Widget offlineNavigation(ColorScheme colors) {
    const destinations = [
      (Icons.home_outlined, 'خانه'),
      (Icons.calendar_month_outlined, 'برنامه شخصی'),
      (Icons.bar_chart_outlined, 'پیشرفت'),
      (Icons.edit_note_outlined, 'گزارش'),
      (Icons.person_outline, 'حساب'),
    ];
    return Material(
      key: const ValueKey('apex-offline-navigation'),
      color: colors.surfaceContainerLow,
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 60,
          child: Row(
            children: [
              for (final (index, (icon, label)) in destinations.indexed)
                Expanded(
                  child: Semantics(
                    selected: index == tab,
                    button: true,
                    child: InkWell(
                      onTap: () => setState(() => tab = index),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 3),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            DecoratedBox(
                              decoration: BoxDecoration(
                                color: index == tab
                                    ? colors.secondaryContainer
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(16),
                              ),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 3,
                                ),
                                child: Icon(
                                  icon,
                                  size: 21,
                                  color: index == tab
                                      ? colors.onSecondaryContainer
                                      : colors.onSurfaceVariant,
                                ),
                              ),
                            ),
                            const SizedBox(height: 3),
                            SizedBox(
                              width: double.infinity,
                              height: 17,
                              child: FittedBox(
                                fit: BoxFit.scaleDown,
                                child: Text(
                                  label,
                                  maxLines: 1,
                                  style: TextStyle(
                                    color: colors.onSurface,
                                    fontSize: 11,
                                    fontWeight: index == tab
                                        ? FontWeight.bold
                                        : FontWeight.w500,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final dark = isDark;
    final theme = offlineTheme;
    return Theme(
      data: theme,
      child: Directionality(
        textDirection: TextDirection.rtl,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('Apex360', textDirection: TextDirection.ltr),
            actions: [
              IconButton(
                tooltip: dark ? 'حالت روز' : 'حالت شب',
                onPressed: ready ? () => toggleTheme(!dark) : null,
                icon: Icon(
                  dark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                ),
              ),
            ],
          ),
          body: loadFailed
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'خواندن اطلاعات ناموفق بود. برای حفاظت از داده‌ها ثبت جدید متوقف شده است.',
                        ),
                        OutlinedButton(
                          onPressed: () {
                            setState(() => loadFailed = false);
                            load();
                          },
                          child: const Text('تلاش مجدد'),
                        ),
                      ],
                    ),
                  ),
                )
              : !ready
                  ? const Center(child: CircularProgressIndicator())
                  : SafeArea(
                      bottom: false,
                      child: ListView(
                        key: ValueKey(tab),
                        controller: switch (tab) {
                          1 => planScroll,
                          3 => reportScroll,
                          _ => null
                        },
                        padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
                        children: [
                          if (!profileComplete) ...[
                            heading('ابتدا پروفایل خود را تکمیل کنید'),
                            account(),
                          ],
                          if (profileComplete && tab == 0) home(),
                          if (profileComplete && tab == 1) plan(),
                          if (profileComplete && tab == 2) progress(),
                          if (profileComplete && tab == 3) report(),
                          if (profileComplete && tab == 4) account(),
                        ],
                      ),
                    ),
          bottomNavigationBar: !ready || !profileComplete
              ? null
              : offlineNavigation(theme.colorScheme),
        ),
      ),
    );
  }
}
