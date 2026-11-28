import 'package:flutter_test/flutter_test.dart';
import 'package:taranom_hamdeli/services/study_momentum.dart';

void main() {
  final now = DateTime(2026, 3, 8);
  StudyEntry entry(int day, int minutes, int tests) =>
      (day: DateTime(2026, 3, day), minutes: minutes, tests: tests);

  test('effort is capped by day and unaffected by splitting entries', () {
    final whole = StudyMomentum([entry(8, 120, 60)], now);
    final split = StudyMomentum([entry(8, 90, 1), entry(8, 30, 59)], now);
    expect(whole.pointsToday, 8);
    expect(split.points, whole.points);
    expect(split.activeDays, 1);
    expect(split.todayMinutes, 120);
  });

  test('a break preserves past effort and best streak', () {
    final effort = StudyMomentum([
      entry(1, 5, 0),
      entry(2, 0, 1),
      entry(3, 5, 0),
      entry(4, 0, 0),
      entry(6, 10, 0),
      entry(9, 40, 10),
    ], now);
    expect(effort.points, 6);
    expect(effort.activeDays, 4);
    expect(effort.streak, 1);
    expect(effort.bestStreak, 3);
    expect(effort.lastActiveDay, DateTime.utc(2026, 3, 6));
    expect(effort.todayMinutes, 0);
  });
}
