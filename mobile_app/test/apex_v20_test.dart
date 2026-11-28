import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:taranom_hamdeli/screens/apex_demo_screen.dart';
import 'package:taranom_hamdeli/screens/wellbeing_screen.dart';
import 'package:taranom_hamdeli/services/focus_session.dart';
import 'package:taranom_hamdeli/theme/education_profile.dart';

void main() {
  test('timers survive serialization, pauses and background expiry', () {
    final start = DateTime.utc(2026, 11, 28, 10);
    final session = FocusSession.start(25, start);
    final paused = session.pause(start.add(const Duration(minutes: 5)));
    final later = start.add(const Duration(hours: 2));
    expect(FocusSession.decode(paused.encode()).remaining(later), 1200);
    final resumed = FocusSession.decode(paused.resume(later).encode());
    expect(resumed.elapsedMinutes(later), 5);
    expect(resumed.remaining(later.add(const Duration(seconds: 1199))), 1);
    expect(resumed.remaining(later.add(const Duration(hours: 1))), 0);
    expect(resumed.elapsedMinutes(later.add(const Duration(hours: 1))), 25);
  });

  test('recognizes all three digit systems for grade nine', () {
    for (final label in ['پایه نهم', '9', '۹', '٩']) {
      expect(isNinthGrade(label), isTrue);
    }
    expect(isNinthGrade('یازدهم'), isFalse);
  });

  testWidgets(
      'focus transfer opens existing report draft and leaves legacy data intact',
      (tester) async {
    const key = 'apex360_focus_v1_personal';
    final fixture = jsonEncode({
      'studentName': 'رها',
      'studentGrade': '۹',
      'studentTrack': 'تجربی',
      'tasks': [],
      'reports': [],
    });
    SharedPreferences.setMockInitialValues({
      'apex360_offline_v1': fixture,
      key: FocusSession.start(
              25, DateTime.now().subtract(const Duration(hours: 1)))
          .encode(),
    });
    await tester.pumpWidget(const MaterialApp(home: ApexDemoScreen()));
    await tester.pumpAndSettle();
    await tester.tap(find.text('زمان‌سنج تمرکز'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('انتقال ۲۵ دقیقه به گزارش'));
    await tester.pumpAndSettle();
    expect(find.text('ثبت گزارش روزانه'), findsOneWidget);
    expect(find.widgetWithText(TextFormField, '25'), findsOneWidget);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString(key), isNull);
    expect(prefs.getString('apex360_offline_v1'), fixture);

    await tester.tap(find.text('حساب'));
    await tester.pumpAndSettle();
    expect(find.text('نهم'), findsOneWidget);
    expect(find.textContaining('تجربی'), findsNothing);
    expect(prefs.getString('apex360_offline_v1'), fixture);
  });

  testWidgets('mood is persisted, separated by scope, and removable',
      (tester) async {
    FlutterSecureStorage.setMockInitialValues({});
    Future<void> open(String scope) async {
      await tester.pumpWidget(MaterialApp(
        home: WellbeingScreen(key: ValueKey(scope), scope: scope),
      ));
      await tester.pumpAndSettle();
    }

    await open('student_1');
    await tester.tap(find.text('آرام'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('ثبت حال امروز'));
    await tester.pumpAndSettle();
    expect(find.text('حال امروز ثبت شده'), findsOneWidget);
    await open('student_2');
    expect(find.text('حال امروز ثبت شده'), findsNothing);
    await open('student_1');
    expect(find.text('حال امروز ثبت شده'), findsOneWidget);
    await tester.tap(find.text('پاک‌کردن حال ثبت‌شده'));
    await tester.pumpAndSettle();
    expect(find.text('حال امروز ثبت شده'), findsNothing);
  });
}
