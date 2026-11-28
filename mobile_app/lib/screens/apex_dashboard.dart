import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:shamsi_date/shamsi_date.dart';

import '../services/study_momentum.dart';
import '../theme/apex_components.dart';
import '../theme/app_theme.dart';
import '../theme/journey_art.dart';

class ApexDashboard extends StatelessWidget {
  const ApexDashboard({
    super.key,
    required this.studentName,
    required this.dateLabel,
    required this.tasks,
    required this.momentum,
    required this.onPlan,
    required this.onReport,
    required this.onToggleTask,
    required this.onFocus,
    required this.onMood,
    required this.onProgress,
  });

  final String studentName, dateLabel;
  final List<Map<String, dynamic>> tasks;
  final StudyMomentum momentum;
  final VoidCallback onPlan, onReport, onFocus, onMood, onProgress;
  final void Function(Map<String, dynamic>, bool) onToggleTask;

  @override
  Widget build(BuildContext context) {
    final done = tasks.where((task) => task['done'] == true).length;
    final allDone = tasks.isNotEmpty && done == tasks.length;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ApexSection('سلام، $studentName', detail: fa(dateLabel)),
        AvaHero(
          title: allDone ? 'همه کارهای امروز تیک خوردن!' : 'قدم بعدی',
          guidance: allDone
              ? 'وقت یک استراحت کوتاهه.'
              : tasks.isEmpty
              ? 'یک مرور کوتاه برای شروع کافیه.'
              : 'از ${tasks.firstWhere((task) => task['done'] != true)['title']} شروع کن.',
          celebrating: allDone || momentum.todayMinutes > 0,
          onPlan: onPlan,
          onReport: onReport,
          onFocus: onFocus,
        ),
        JourneyActions(onMood: onMood, onProgress: onProgress),
        MissionBoard(momentum: momentum, onFocus: onFocus, onReport: onReport),
        ApexSection(
          'هدف‌های امروز',
          detail: tasks.isEmpty
              ? 'برای امروز یک تکلیف کوچک انتخاب کن.'
              : '${fa(done)} از ${fa(tasks.length)} تکلیف انجام شد',
        ),
        for (final task in tasks)
          Card(
            child: CheckboxListTile(
              title: Text(task['title'].toString()),
              subtitle: Text('${fa(task['plannedMinutes'] ?? 0)} دقیقه'),
              secondary: SubjectMark(task['title'].toString()),
              value: task['done'] == true,
              onChanged: (value) => onToggleTask(task, value ?? false),
            ),
          ),
        OutlinedButton.icon(
          onPressed: onPlan,
          icon: const Icon(Icons.calendar_today_outlined),
          label: const Text('برنامه‌ریزی امروز'),
        ),
      ],
    );
  }
}

class JourneyActions extends StatelessWidget {
  const JourneyActions({
    super.key,
    required this.onMood,
    required this.onProgress,
  });
  final VoidCallback onMood, onProgress;

  @override
  Widget build(BuildContext context) {
    final c = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final (index, (label, icon, bg, fg, action)) in [
            (
              'حال روزانه',
              Icons.sentiment_satisfied_alt,
              c.secondaryContainer,
              c.onSecondaryContainer,
              onMood,
            ),
            (
              'پیشرفت من',
              Icons.explore_outlined,
              c.tertiaryContainer,
              c.onTertiaryContainer,
              onProgress,
            ),
          ].indexed) ...[
            if (index > 0) const SizedBox(width: 8),
            Expanded(
              child: Material(
                color: bg,
                borderRadius: BorderRadius.circular(20),
                child: InkWell(
                  borderRadius: BorderRadius.circular(20),
                  onTap: action,
                  child: Padding(
                    padding: const EdgeInsets.all(10),
                    child: Column(
                      children: [
                        Icon(icon, color: fg, size: 25),
                        const SizedBox(height: 4),
                        Text(
                          label,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.labelLarge
                              ?.copyWith(color: fg),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class AvaHero extends StatelessWidget {
  const AvaHero({
    super.key,
    required this.title,
    required this.guidance,
    required this.celebrating,
    required this.onPlan,
    required this.onReport,
    required this.onFocus,
  });
  final String title, guidance;
  final bool celebrating;
  final VoidCallback onPlan, onReport, onFocus;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(32),
      child: ColoredBox(
        color: const Color(0xFF102443),
        child: CustomPaint(
          painter: const NightLandscape(),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            celebrating
                                ? 'آوا · همراه قدم امروز'
                                : 'آوا · همراه مسیر تو',
                            style: theme.textTheme.labelLarge?.copyWith(
                              color: const Color(0xFFC6DCFF),
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            title,
                            style: theme.textTheme.titleLarge?.copyWith(
                              color: Colors.white,
                            ),
                          ),
                          Text(
                            guidance,
                            style: const TextStyle(color: Colors.white),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 4),
                    IconButton(
                      tooltip: 'از آوا کمک بگیر',
                      onPressed: () => showAva(
                        context,
                        guidance: guidance,
                        onPlan: onPlan,
                        onReport: onReport,
                      ),
                      icon: AvaCompanion(celebrating: celebrating, size: 96),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFFCDE0FF),
                    foregroundColor: const Color(0xFF102443),
                  ),
                  onPressed: onFocus,
                  icon: const Icon(Icons.timer_outlined),
                  label: const Text('زمان‌سنج تمرکز'),
                ),
                TextButton.icon(
                  style: TextButton.styleFrom(
                    foregroundColor: Colors.white,
                    minimumSize: const Size(48, 48),
                  ),
                  onPressed: onReport,
                  icon: const Icon(Icons.edit_note),
                  label: const Text('ثبت مطالعه'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class MissionBoard extends StatelessWidget {
  const MissionBoard({
    super.key,
    required this.momentum,
    required this.onFocus,
    required this.onReport,
  });
  final StudyMomentum momentum;
  final VoidCallback onFocus, onReport;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final c = theme.colorScheme;
    final steps = [
      (
        'قدم اول',
        'یک فعالیت ثبت کن',
        Icons.flag_rounded,
        momentum.todayMinutes > 0 || momentum.todayTests > 0,
        c.primaryContainer,
        c.onPrimaryContainer,
        onReport,
      ),
      (
        'جزیرهٔ تمرکز',
        '۲۵ دقیقه مطالعه',
        Icons.timer_outlined,
        momentum.todayMinutes >= 25,
        c.secondaryContainer,
        c.onSecondaryContainer,
        onFocus,
      ),
      (
        'قلهٔ تمرین',
        'تمرین یا تست ثبت کن',
        Icons.landscape_rounded,
        momentum.todayTests > 0,
        c.tertiaryContainer,
        c.onTertiaryContainer,
        onReport,
      ),
    ];
    final count = steps.where((step) => step.$4).length;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'نقشهٔ مأموریت‌های امروز',
                        style: theme.textTheme.titleLarge,
                      ),
                      Text('${fa(momentum.todayMinutes)} دقیقه مطالعه'),
                      Text('${fa(momentum.todayTests)} تست'),
                    ],
                  ),
                ),
                ProgressRing(
                  value: count / steps.length,
                  label: '${fa(count)} از ۳',
                ),
              ],
            ),
            const SizedBox(height: 10),
            CustomPaint(
              painter: TrailPainter(
                c.outline,
                Directionality.of(context) == TextDirection.rtl,
              ),
              child: Column(
                children: [
                  for (final (title, detail, icon, done, bg, fg, action)
                      in steps)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Semantics(
                        label: done ? '$title، انجام شد' : null,
                        child: ListTile(
                          contentPadding: EdgeInsets.zero,
                          onTap: action,
                          leading: CircleAvatar(
                            radius: 25,
                            backgroundColor: bg,
                            foregroundColor: fg,
                            child: Icon(done ? Icons.check_rounded : icon),
                          ),
                          title: Text(
                            title,
                            style: theme.textTheme.titleMedium,
                          ),
                          subtitle: Text(detail),
                          trailing: const Icon(Icons.chevron_left_rounded),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const Divider(height: 20),
            if (count == steps.length)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  Icons.workspace_premium_rounded,
                  color: c.primary,
                ),
                title: const Text('نشانِ مسیر کاملِ امروز'),
              ),
            Text(
              '${fa(momentum.pointsToday)} امتیاز تلاش امروز',
              style: theme.textTheme.labelLarge,
            ),
          ],
        ),
      ),
    );
  }
}

class ProgressRing extends StatelessWidget {
  const ProgressRing({super.key, required this.value, required this.label});
  final double value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Semantics(
      label: label,
      child: ExcludeSemantics(
        child: SizedBox.square(
          dimension: 72,
          child: Stack(
            fit: StackFit.expand,
            children: [
              TweenAnimationBuilder<double>(
                tween: Tween(end: value),
                duration: MediaQuery.disableAnimationsOf(context)
                    ? Duration.zero
                    : const Duration(milliseconds: 240),
                builder: (_, progress, child) => CircularProgressIndicator(
                  value: progress,
                  strokeWidth: 7,
                  strokeCap: StrokeCap.round,
                  backgroundColor: colors.secondaryContainer,
                ),
              ),
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(10),
                  child: FittedBox(child: Text(label)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class StudyAchievements extends StatelessWidget {
  const StudyAchievements({super.key, required this.momentum});
  final StudyMomentum momentum;

  @override
  Widget build(BuildContext context) {
    final c = Theme.of(context).colorScheme;
    final last = momentum.lastActiveDay;
    final jalali = last == null ? null : Jalali.fromDateTime(last);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'جعبهٔ دستاوردها',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            Text(
              '${fa(momentum.points)} امتیاز تلاش · ${fa(momentum.activeDays)} روز مطالعه',
            ),
            if (jalali != null)
              Text(
                'تا ${fa(jalali.day)}/${fa(jalali.month)}، ${fa(momentum.streak)} روز پیوسته',
              ),
            const SizedBox(height: 8),
            const SizedBox(height: 6),
            CustomPaint(
              painter: TrailPainter(
                c.outline,
                Directionality.of(context) == TextDirection.rtl,
              ),
              child: Column(
                children: [
                  for (final (name, detail, earned) in [
                    (
                      'اولین قدم',
                      'یک روز فعالیت ثبت‌شده',
                      momentum.activeDays > 0,
                    ),
                    (
                      'سه روز مطالعه',
                      'فعالیت در سه روز متفاوت',
                      momentum.activeDays >= 3,
                    ),
                    (
                      'سه روز پیوسته',
                      'فعالیت در سه روز پشت‌سرهم',
                      momentum.bestStreak >= 3,
                    ),
                    (
                      'کاشف مسیر',
                      'فعالیت در هفت روز متفاوت',
                      momentum.activeDays >= 7,
                    ),
                  ])
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: CircleAvatar(
                          radius: 25,
                          backgroundColor: earned
                              ? c.tertiaryContainer
                              : c.surfaceContainerHighest,
                          foregroundColor: earned
                              ? c.onTertiaryContainer
                              : c.onSurface,
                          child: Icon(
                            earned
                                ? Icons.workspace_premium_rounded
                                : Icons.flag_outlined,
                          ),
                        ),
                        title: Text(name),
                        subtitle: Text(detail),
                        trailing: Icon(
                          earned ? Icons.check_rounded : Icons.more_horiz,
                          semanticLabel: earned ? 'به دست آمد' : 'هدف بعدی',
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> showAva(
  BuildContext context, {
  required String guidance,
  required VoidCallback onPlan,
  required VoidCallback onReport,
}) => showModalBottomSheet<void>(
  context: context,
  showDragHandle: true,
  isScrollControlled: true,
  useSafeArea: true,
  builder: (sheet) => SafeArea(
    child: Directionality(
      textDirection: TextDirection.rtl,
      child: ListView(
        shrinkWrap: true,
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 22),
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.night,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              children: [
                const AvaCompanion(celebrating: false, focused: true),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'آوا، همراه مطالعه',
                        style: TextStyle(
                          color: AppColors.mint,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        guidance,
                        style: const TextStyle(color: Colors.white),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          ListTile(
            leading: const Icon(Icons.event_available_rounded),
            title: const Text('کار بعدی رو انتخاب کن'),
            subtitle: const Text('یک درس بردار و با ۱۵ دقیقه شروع کن.'),
            onTap: () {
              Navigator.pop(sheet);
              onPlan();
            },
          ),
          const ExpansionTile(
            leading: Icon(Icons.lightbulb_outline),
            title: Text('روش مرور آوا'),
            children: [
              Padding(
                padding: EdgeInsets.fromLTRB(16, 0, 16, 16),
                child: Text(
                  'کتاب را ببند و سه نکته را از حافظه بگو. بعد پاسخ‌هایت را با کتاب بررسی کن.',
                ),
              ),
            ],
          ),
          ListTile(
            leading: const Icon(Icons.edit_note_rounded),
            title: const Text('نتیجه‌ات رو ثبت کن'),
            subtitle: const Text('زمان مطالعه و تعداد تست‌هایی که زدی.'),
            onTap: () {
              Navigator.pop(sheet);
              onReport();
            },
          ),
        ],
      ),
    ),
  ),
);

class AvaCompanion extends StatelessWidget {
  const AvaCompanion({
    super.key,
    required this.celebrating,
    this.focused = false,
    this.size = 72,
  });
  final bool celebrating, focused;
  final double size;

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: AnimatedSwitcher(
      duration: MediaQuery.disableAnimationsOf(context)
          ? Duration.zero
          : const Duration(milliseconds: 180),
      transitionBuilder: (child, animation) => ScaleTransition(
        scale: Tween<double>(begin: .93, end: 1).animate(animation),
        child: FadeTransition(opacity: animation, child: child),
      ),
      child: CustomPaint(
        key: ValueKey((celebrating, focused)),
        size: Size.square(size),
        painter: _AvaPainter(celebrating, focused),
      ),
    ),
  );
}

class _AvaPainter extends CustomPainter {
  const _AvaPainter(this.celebrating, this.focused);
  final bool celebrating, focused;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.scale(size.width / 100, size.height / 100);
    final orbit = Paint()
      ..color = focused ? const Color(0xFF86A9F8) : const Color(0xFF5D8297)
      ..strokeWidth = 1.4
      ..style = PaintingStyle.stroke;
    canvas.save();
    canvas.translate(50, 50);
    canvas.rotate(-.6);
    canvas.drawOval(const Rect.fromLTWH(-44, -26, 88, 52), orbit);
    canvas.restore();

    final paint = Paint()..color = const Color(0xFF5BC7AE);
    canvas.drawPath(
      Path()
        ..moveTo(65, 38)
        ..quadraticBezierTo(80, 43, 93, 20)
        ..quadraticBezierTo(89, 51, 78, 59)
        ..lineTo(82, 60)
        ..quadraticBezierTo(73, 71, 58, 72)
        ..close(),
      paint,
    );
    paint.color = AppColors.mint;
    canvas.drawPath(
      Path()
        ..moveTo(18, 61)
        ..cubicTo(9, 46, 28, 25, 47, 27)
        ..cubicTo(64, 23, 78, 44, 73, 60)
        ..cubicTo(67, 85, 23, 86, 18, 61)
        ..close(),
      paint,
    );
    paint.color = const Color(0xFFFCC66E);
    for (final (x, y) in [
      (21.0, 26.0),
      (78.0, 78.0),
      (54.0, 12.0),
      if (celebrating) ...[(14.0, 80.0), (84.0, 12.0), (65.0, 91.0)],
    ]) {
      canvas.drawPath(
        Path()
          ..moveTo(x, y - 5)
          ..lineTo(x + 2, y - 2)
          ..lineTo(x + 5, y)
          ..lineTo(x + 2, y + 2)
          ..lineTo(x, y + 5)
          ..lineTo(x - 2, y + 2)
          ..lineTo(x - 5, y)
          ..lineTo(x - 2, y - 2)
          ..close(),
        paint,
      );
    }
    paint.color = AppColors.night;
    final line = Paint()
      ..color = AppColors.night
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.4
      ..strokeCap = StrokeCap.round;
    for (final x in [34.0, 55.0]) {
      if (celebrating || focused) {
        canvas.drawArc(
          Rect.fromCenter(center: Offset(x, 54), width: 9, height: 8),
          celebrating ? math.pi : 0,
          math.pi,
          false,
          line,
        );
      } else {
        canvas.drawOval(
          Rect.fromCenter(center: Offset(x, 52), width: 6, height: 9),
          paint,
        );
      }
    }
    canvas.drawArc(const Rect.fromLTWH(41, 55, 8, 9), 0, math.pi, false, line);
  }

  @override
  bool shouldRepaint(_AvaPainter oldDelegate) =>
      oldDelegate.celebrating != celebrating || oldDelegate.focused != focused;
}

class ApexWeekChart extends StatefulWidget {
  const ApexWeekChart({
    super.key,
    required this.title,
    required this.unit,
    required this.days,
  });

  final String title;
  final String unit;
  final List<({String label, int value})> days;

  @override
  State<ApexWeekChart> createState() => _ApexWeekChartState();
}

class _ApexWeekChartState extends State<ApexWeekChart> {
  int? _selection;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final days = widget.days;
    final selected = days.isEmpty
        ? 0
        : (_selection ?? days.length - 1).clamp(0, days.length - 1).toInt();
    final maximum = days.fold<int>(
      1,
      (highest, day) => math.max(day.value, highest),
    );
    final colors = theme.colorScheme;
    final total = days.fold<int>(0, (sum, day) => sum + day.value);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(widget.title, style: theme.textTheme.titleMedium),
            Text('مجموع هفت روز · ${fa(total)} ${widget.unit}'),
            const SizedBox(height: 6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                for (final (index, day) in days.indexed)
                  Expanded(
                    child: Semantics(
                      button: true,
                      onTap: () => setState(() => _selection = index),
                      selected: index == selected,
                      label: '${day.label}، ${fa(day.value)} ${widget.unit}',
                      child: ExcludeSemantics(
                        child: InkWell(
                          borderRadius: BorderRadius.circular(10),
                          onTap: () => setState(() => _selection = index),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 3,
                              vertical: 6,
                            ),
                            child: Column(
                              children: [
                                SizedBox(
                                  height: 80,
                                  child: Align(
                                    alignment: Alignment.bottomCenter,
                                    child: Container(
                                      height:
                                          4 +
                                          76 *
                                              (day.value / maximum)
                                                  .clamp(0.0, 1.0)
                                                  .toDouble(),
                                      width: 18,
                                      decoration: BoxDecoration(
                                        color: index == selected
                                            ? colors.primary
                                            : colors.secondaryContainer,
                                        border: index == selected
                                            ? Border.all(
                                                color:
                                                    theme.colorScheme.onSurface,
                                                width: 1.5,
                                              )
                                            : null,
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 5),
                                FittedBox(
                                  child: Text(
                                    fa(day.label),
                                    textDirection: TextDirection.ltr,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            if (days.isNotEmpty)
              Text(
                'روز ${fa(days[selected].label)} · ${fa(days[selected].value)} ${widget.unit}',
                style: theme.textTheme.labelLarge,
              ),
          ],
        ),
      ),
    );
  }
}
