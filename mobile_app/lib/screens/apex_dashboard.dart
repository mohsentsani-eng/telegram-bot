import 'dart:math' as math;

import 'package:flutter/material.dart';

class ApexDashboard extends StatelessWidget {
  const ApexDashboard({
    super.key,
    required this.studentName,
    required this.dateLabel,
    required this.tasks,
    required this.reports,
    required this.onPlan,
    required this.onReport,
    required this.onToggleTask,
  });

  final String studentName;
  final String dateLabel;
  final List<Map<String, dynamic>> tasks;
  final List<Map<String, dynamic>> reports;
  final VoidCallback onPlan;
  final VoidCallback onReport;
  final void Function(Map<String, dynamic>, bool) onToggleTask;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final done = tasks.where((task) => task['done'] == true).length;
    final minutes = reports.fold<int>(
      0,
      (sum, row) => sum + (row['minutes'] as int),
    );
    final tests = reports.fold<int>(
      0,
      (sum, row) => sum + (row['tests'] as int),
    );
    final allDone = tasks.isNotEmpty && done == tasks.length;
    final guidance = tasks.isEmpty
        ? 'با یک کار کوچک شروع کن. دوست داری امروز چه درسی رو مرور کنی؟'
        : allDone
            ? 'همه کارهای امروز تیک خوردن! وقت یه استراحت کوتاهه.'
            : 'یکی از کارهای امروز رو انتخاب کن. قدم بعدی همون یک کاره!';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(28),
            gradient: const LinearGradient(
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
              colors: [Color(0xFF4B328D), Color(0xFF265087), Color(0xFF146469)],
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(dateLabel, style: const TextStyle(color: Colors.white70)),
                const SizedBox(height: 8),
                Text(
                  'سلام، $studentName',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    ExcludeSemantics(
                      child: CustomPaint(
                        size: const Size(66, 66),
                        painter: _CompanionPainter(celebrating: allDone),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'آوا، همراه مطالعه‌ات\n$guidance',
                        style: const TextStyle(
                          color: Colors.white,
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                LinearProgressIndicator(
                  value: tasks.isEmpty ? 0 : done / tasks.length,
                  color: const Color(0xFFAAEEE2),
                  backgroundColor: Colors.white24,
                  borderRadius: BorderRadius.circular(8),
                  minHeight: 8,
                  semanticsLabel: 'پیشرفت برنامه امروز',
                ),
                const SizedBox(height: 8),
                Text(
                  '$done از ${tasks.length} تکلیف انجام شده',
                  style: const TextStyle(color: Colors.white),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            Chip(
              avatar: const Icon(Icons.timer_outlined),
              label: Text('$minutes دقیقه مطالعه'),
            ),
            Chip(
              avatar: const Icon(Icons.quiz_outlined),
              label: Text('$tests تست'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton.icon(
              onPressed: onPlan,
              icon: const Icon(Icons.event),
              label: const Text('برنامه‌ریزی امروز'),
            ),
            OutlinedButton.icon(
              onPressed: onReport,
              icon: const Icon(Icons.edit_note),
              label: const Text('ثبت گزارش مطالعه'),
            ),
          ],
        ),
        const SizedBox(height: 20),
        Text('مأموریت‌های امروز', style: theme.textTheme.titleLarge),
        const SizedBox(height: 6),
        if (tasks.isEmpty) const Text('هنوز تکلیفی برای امروز ثبت نشده است.'),
        for (final task in tasks)
          Card(
            child: CheckboxListTile(
              title: Text(task['title'].toString()),
              subtitle: Text('${task['plannedMinutes'] ?? 0} دقیقه'),
              value: task['done'] == true,
              onChanged: (value) => onToggleTask(task, value ?? false),
            ),
          ),
      ],
    );
  }
}

class _CompanionPainter extends CustomPainter {
  const _CompanionPainter({required this.celebrating});

  final bool celebrating;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 66, size.height / 66);
    final paint = Paint()..color = Colors.white24;
    canvas.drawCircle(const Offset(33, 33), 33, paint);
    paint.color = const Color(0xFFC6F7EC);
    canvas.drawLine(
      const Offset(33, 14),
      const Offset(33, 24),
      paint..strokeWidth = 3,
    );
    canvas.drawCircle(const Offset(33, 13), 4, paint);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        const Rect.fromLTWH(10, 22, 46, 32),
        const Radius.circular(13),
      ),
      paint,
    );
    paint.color = const Color(0xFF233560);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        const Rect.fromLTWH(16, 28, 34, 20),
        const Radius.circular(8),
      ),
      paint,
    );
    paint.color = const Color(0xFFE4FCF9);
    for (final x in [25.0, 41.0]) {
      if (celebrating) {
        canvas.drawArc(
          Rect.fromCenter(center: Offset(x, 37), width: 7, height: 7),
          math.pi,
          math.pi,
          false,
          paint..style = PaintingStyle.stroke,
        );
        paint.style = PaintingStyle.fill;
      } else {
        canvas.drawCircle(Offset(x, 36), 2.6, paint);
      }
    }
    canvas.drawArc(
      const Rect.fromLTWH(30, 37, 6, 7),
      0,
      math.pi,
      false,
      paint
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5,
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(_CompanionPainter oldDelegate) =>
      oldDelegate.celebrating != celebrating;
}

class ApexWeekChart extends StatelessWidget {
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
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final maximum = days.fold<int>(
      1,
      (highest, day) => math.max(day.value, highest),
    );
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(title, style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            for (final day in days)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: MergeSemantics(
                    child: Row(
                  children: [
                    SizedBox(
                      width: 49,
                      child: Text(day.label, textDirection: TextDirection.ltr),
                    ),
                    Expanded(
                      child: ExcludeSemantics(
                        child: LinearProgressIndicator(
                          value: day.value < 0 ? 0 : day.value / maximum,
                          minHeight: 8,
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    SizedBox(width: 70, child: Text('${day.value} $unit')),
                  ],
                )),
              ),
          ],
        ),
      ),
    );
  }
}
