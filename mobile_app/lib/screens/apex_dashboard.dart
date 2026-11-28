import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:shamsi_date/shamsi_date.dart';

import '../services/study_momentum.dart';
import '../theme/apex_components.dart';
import '../theme/app_theme.dart';

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
  });

  final String studentName, dateLabel;
  final List<Map<String, dynamic>> tasks;
  final StudyMomentum momentum;
  final VoidCallback onPlan, onReport;
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
        ),
        MissionBoard(momentum: momentum),
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

class AvaHero extends StatelessWidget {
  const AvaHero({
    super.key,
    required this.title,
    required this.guidance,
    required this.celebrating,
    required this.onPlan,
    required this.onReport,
    this.actionLabel = 'ثبت مطالعه',
  });
  final String title, guidance, actionLabel;
  final bool celebrating;
  final VoidCallback onPlan, onReport;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: AppColors.night,
          borderRadius: BorderRadius.circular(28),
        ),
        padding: const EdgeInsets.all(16),
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
                        'آوا، همراه مطالعه',
                        style: Theme.of(context)
                            .textTheme
                            .labelLarge
                            ?.copyWith(color: AppColors.mint),
                      ),
                      Text(
                        title,
                        style: Theme.of(context)
                            .textTheme
                            .titleLarge
                            ?.copyWith(color: Colors.white),
                      ),
                      Text(guidance,
                          style: const TextStyle(color: Colors.white)),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                AvaCompanion(celebrating: celebrating, size: 94),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.mint,
                    foregroundColor: AppColors.night,
                  ),
                  onPressed: onReport,
                  icon: const Icon(Icons.edit_note),
                  label: Text(actionLabel),
                ),
                TextButton(
                  style: TextButton.styleFrom(
                    foregroundColor: AppColors.mint,
                    minimumSize: const Size(48, 48),
                  ),
                  onPressed: () => showAva(
                    context,
                    guidance: guidance,
                    onPlan: onPlan,
                    onReport: onReport,
                  ),
                  child: const Text('از آوا کمک بگیر'),
                ),
              ],
            ),
          ],
        ),
      );
}

class MissionBoard extends StatelessWidget {
  const MissionBoard({super.key, required this.momentum});
  final StudyMomentum momentum;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final missions = [
      ('یک قدم کوچک', momentum.todayMinutes > 0 || momentum.todayTests > 0),
      ('۲۵ دقیقه تمرکز', momentum.todayMinutes >= 25),
      ('تمرین بازیابی', momentum.todayTests > 0),
    ];
    final achieved = missions.where((mission) => mission.$2).length;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
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
                          'مأموریت‌های امروز',
                          style: theme.textTheme.titleLarge,
                        ),
                        Text('${fa(momentum.todayMinutes)} دقیقه مطالعه'),
                        Text('${fa(momentum.todayTests)} تست'),
                      ],
                    ),
                  ),
                  ProgressRing(
                    value: achieved / missions.length,
                    label: '${fa(achieved)} از ۳',
                  ),
                ],
              ),
              const SizedBox(height: 8),
              for (final (label, done) in missions)
                Row(
                  children: [
                    Icon(
                      done ? Icons.check_circle_rounded : Icons.circle_outlined,
                      size: 19,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: Text(label)),
                    if (done) const Text('انجام شد'),
                  ],
                ),
              const Divider(height: 22),
              Text(
                '${fa(momentum.pointsToday)} امتیاز تلاش امروز',
                style: theme.textTheme.labelLarge,
              ),
            ],
          ),
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
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final (name, earned) in [
                  ('اولین قدم', momentum.activeDays > 0),
                  ('سه روز مطالعه', momentum.activeDays >= 3),
                  ('سه روز پیوسته', momentum.bestStreak >= 3),
                ])
                  Chip(
                    avatar: Icon(
                      earned
                          ? Icons.workspace_premium_rounded
                          : Icons.flag_outlined,
                      color:
                          earned ? c.onTertiaryContainer : c.onSurfaceVariant,
                    ),
                    backgroundColor: earned ? c.tertiaryContainer : c.surface,
                    label: Text(
                      name,
                      semanticsLabel:
                          '$name، ${earned ? "به دست آمد" : "هدف بعدی"}',
                      style: TextStyle(
                        color: earned ? c.onTertiaryContainer : c.onSurface,
                      ),
                    ),
                  ),
              ],
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
}) =>
    showModalBottomSheet<void>(
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
                        'کتاب را ببند و سه نکته را از حافظه بگو. بعد پاسخ‌هایت را با کتاب بررسی کن.'),
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
      ..color = const Color(0xFF40616A)
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
    for (final (x, y) in [(21.0, 26.0), (78.0, 78.0), (54.0, 12.0)]) {
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
                                  height: 62,
                                  child: Align(
                                    alignment: Alignment.bottomCenter,
                                    child: Container(
                                      height: 4 +
                                          58 *
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
