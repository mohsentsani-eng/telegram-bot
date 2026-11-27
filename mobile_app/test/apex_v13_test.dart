import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:taranom_hamdeli/screens/apex_dashboard.dart';
import 'package:taranom_hamdeli/screens/apex_demo_screen.dart';

const legacyKey = 'apex360_offline_v1';

Future<void> openApp(WidgetTester tester) async {
  await tester.pumpWidget(const MaterialApp(home: ApexDemoScreen()));
  await tester.pumpAndSettle();
}

Future<void> tapInList(WidgetTester tester, Finder target) async {
  final visibleTarget = target.hitTestable();
  await tester.dragUntilVisible(
    visibleTarget,
    find.byType(ListView),
    const Offset(0, -180),
  );
  await tester.tap(visibleTarget);
  await tester.pumpAndSettle();
}

void main() {
  WidgetController.hitTestWarningShouldBeFatal = true;
  late Map<String, dynamic> legacyData;
  late String fixture;

  setUp(() {
    final today = DateTime.now().toIso8601String().substring(0, 10);
    legacyData = {
      'studentName': 'دانش‌آموز آزمایشی',
      'studentGrade': 'هشتم',
      'studentTrack': '',
      'tasks': [
        {
          'title': 'ریاضی',
          'date': today,
          'topic': 'کسرها',
          'plannedMinutes': 35,
          'priority': 1,
          'done': false,
        },
      ],
      'reports': [
        {
          'subject': 'علوم',
          'date': today,
          'minutes': 25,
          'tests': 3,
          'satisfaction': 7,
          'mood': 3,
          'stress': 3,
          'note': 'نمونه',
        },
      ],
    };
    fixture = jsonEncode(legacyData);
    SharedPreferences.setMockInitialValues({legacyKey: fixture});
  });

  testWidgets('v12 data loads and switching theme leaves its bytes intact', (
    tester,
  ) async {
    await openApp(tester);
    expect(find.text('سلام، دانش‌آموز آزمایشی'), findsOneWidget);
    expect(find.text('25 دقیقه مطالعه'), findsOneWidget);
    expect(
      Theme.of(tester.element(find.byType(ApexDashboard))).brightness,
      Brightness.light,
    );

    await tester.tap(find.byTooltip('حالت شب'));
    await tester.pumpAndSettle();
    expect(
      Theme.of(tester.element(find.byType(ApexDashboard))).brightness,
      Brightness.dark,
    );

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString(legacyKey), fixture);
    await tester.pumpWidget(const SizedBox.shrink());
    await openApp(tester);
    expect(find.byTooltip('حالت روز'), findsOneWidget);
    await tester.tap(find.byTooltip('حالت روز'));
    await tester.pumpAndSettle();
    expect(prefs.getString(legacyKey), fixture);
  });

  testWidgets('dashboard task updates preserve v12 reports and profile', (
    tester,
  ) async {
    await openApp(tester);
    final task = find.byType(CheckboxListTile);
    await tapInList(tester, task);

    final prefs = await SharedPreferences.getInstance();
    final stored =
        jsonDecode(prefs.getString(legacyKey)!) as Map<String, dynamic>;
    expect(stored['reports'], legacyData['reports']);
    expect(stored['studentName'], legacyData['studentName']);
    expect(stored['studentGrade'], legacyData['studentGrade']);
    final originalTask = (legacyData['tasks'] as List).single as Map;
    expect((stored['tasks'] as List).single, {...originalTask, 'done': true});
    await tester.drag(find.byType(ListView), const Offset(0, 650));
    await tester.pumpAndSettle();
    expect(find.textContaining('همه کارهای امروز تیک خوردن'), findsOneWidget);
  });

  testWidgets('weekly charts aggregate minutes and tests from legacy reports', (
    tester,
  ) async {
    await openApp(tester);
    await tester.tap(find.text('پیشرفت'));
    await tester.pumpAndSettle();

    final charts =
        tester.widgetList<ApexWeekChart>(find.byType(ApexWeekChart)).toList();
    expect(charts, hasLength(2));
    expect(charts[0].days.map((day) => day.value), [0, 0, 0, 0, 0, 0, 25]);
    expect(charts[1].days.map((day) => day.value), [0, 0, 0, 0, 0, 0, 3]);
  });

  testWidgets(
    'planner opens a linked study report and saves it with its task',
    (tester) async {
      await openApp(tester);
      await tester.tap(find.text('برنامه'));
      await tester.pumpAndSettle();

      final reportAction = find.text('ثبت مطالعه');
      await tapInList(tester, reportAction);
      expect(find.text('اتصال گزارش به تکلیف برنامه'), findsOneWidget);
      final done = find.text('این تکلیف را کامل انجام دادم');
      await tapInList(tester, done);
      final save = find.text('ذخیره گزارش روی گوشی');
      await tapInList(tester, save);

      final prefs = await SharedPreferences.getInstance();
      final stored =
          jsonDecode(prefs.getString(legacyKey)!) as Map<String, dynamic>;
      expect((stored['tasks'] as List).single['done'], true);
      expect((stored['reports'] as List).first['linkedTitle'], 'ریاضی');
      expect(
        (stored['reports'] as List).last,
        (legacyData['reports'] as List).single,
      );
    },
  );
}
