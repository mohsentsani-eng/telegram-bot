import 'dart:math' as math;

typedef StudyEntry = ({DateTime day, int minutes, int tests});

class StudyMomentum {
  StudyMomentum(Iterable<StudyEntry> entries, DateTime now) {
    final today = _day(now);
    final daily = <DateTime, (int, int)>{};
    for (final entry in entries) {
      final day = _day(entry.day);
      if (day.isAfter(today)) continue;
      final (minutes, tests) = daily[day] ?? (0, 0);
      daily[day] = (
        minutes + math.max(0, entry.minutes),
        tests + math.max(0, entry.tests),
      );
    }
    final (minutesToday, testsToday) = daily[today] ?? (0, 0);
    todayMinutes = minutesToday;
    todayTests = testsToday;
    final active = daily.keys.where((day) {
      final (minutes, tests) = daily[day]!;
      return minutes > 0 || tests > 0;
    }).toList()
      ..sort();
    activeDays = active.length;
    DateTime? previous;
    for (final day in active) {
      final (minutes, tests) = daily[day]!;
      points += math.min(minutes ~/ 5, 6) + (tests > 0 ? 2 : 0);
      streak = previous != null && day.difference(previous).inDays == 1
          ? streak + 1
          : 1;
      bestStreak = math.max(bestStreak, streak);
      previous = day;
    }
    lastActiveDay = previous;
  }

  int get pointsToday =>
      math.min(todayMinutes ~/ 5, 6) + (todayTests > 0 ? 2 : 0);
  int points = 0, todayMinutes = 0, todayTests = 0;
  int activeDays = 0, streak = 0, bestStreak = 0;
  DateTime? lastActiveDay;

  static DateTime _day(DateTime date) =>
      DateTime.utc(date.year, date.month, date.day);
}
