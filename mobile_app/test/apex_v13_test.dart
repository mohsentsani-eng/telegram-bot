import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:taranom_hamdeli/screens/apex_dashboard.dart';
import 'package:taranom_hamdeli/screens/apex_demo_screen.dart';
import 'package:taranom_hamdeli/services/encrypted_backup.dart';

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
      'studentTrack': 'تجربی',
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
          'minutes': 45,
          'tests': 21,
          'satisfaction': 7,
          'mood': 3,
          'stress': 3,
          'note': 'نمونه',
        },
        for (final (subject, minutes, tests) in [
          ('ریاضی', 60, 35),
          ('زیست', 75, 40),
          ('شیمی', 90, 60),
        ])
          {
            'subject': subject,
            'date': today,
            'minutes': minutes,
            'tests': tests,
            'satisfaction': 7,
            'mood': 3,
            'stress': 3,
            'note': '',
          },
      ],
    };
    fixture = jsonEncode(legacyData);
    SharedPreferences.setMockInitialValues({legacyKey: fixture});
  });

  testWidgets('personal plan title fits the narrow navigation bar', (tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await openApp(tester);

    final label = find.text('برنامه شخصی');
    final bar = find.byType(NavigationBar);
    expect(tester.getRect(bar).contains(tester.getRect(label).bottomCenter), isTrue);
    await tester.tap(label);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('authenticated backup restores profile and reports after confirmation', (tester) async {
    const password = 'synthetic-backup-password';
    final previous = jsonEncode({...legacyData, 'studentName': 'پروفایل آزمایشی دیگر'});
    SharedPreferences.setMockInitialValues({legacyKey: previous});
    final payload = jsonEncode({...legacyData, 'format': 'apex360-backup-v1'});
    final restored = await tester.runAsync(() async {
      final bytes = await EncryptedBackup.encode(payload, password);
      final envelope = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
      expect(envelope['format'], 'apex360-encrypted-v1');
      expect(utf8.decode(bytes), isNot(contains('studentName')));
      await expectLater(EncryptedBackup.decode(bytes, 'incorrect-password'), throwsA(isA<Exception>()));
      final cipher = base64Decode(envelope['cipher'] as String);
      cipher[0] ^= 1;
      envelope['cipher'] = base64Encode(cipher);
      final tampered = utf8.encode(jsonEncode(envelope));
      await expectLater(EncryptedBackup.decode(tampered, password), throwsA(isA<Exception>()));
      return EncryptedBackup.decode(bytes, password);
    });
    expect(restored, payload);
    await openApp(tester);
    final dynamic screen = tester.state(find.byType(ApexDemoScreen));
    final prefs = await SharedPreferences.getInstance();

    final Future<void> canceled = screen.restoreBackup(suppliedRaw: restored);
    await tester.pumpAndSettle();
    await tester.tap(find.text('انصراف'));
    await tester.pumpAndSettle();
    await canceled;
    expect(prefs.getString(legacyKey), previous);

    final Future<void> confirmed = screen.restoreBackup(suppliedRaw: restored);
    await tester.pumpAndSettle();
    await tester.tap(find.text('بازیابی'));
    await tester.pumpAndSettle();
    await confirmed;
    expect(jsonDecode(prefs.getString(legacyKey)!), legacyData);
    expect(prefs.getString('${legacyKey}_before_restore'), previous);
  });

  testWidgets('v15-shaped data loads and switching theme leaves its bytes intact', (
    tester,
  ) async {
    await openApp(tester);
    expect(find.text('سلام، دانش‌آموز آزمایشی'), findsOneWidget);
    expect(find.text('270 دقیقه مطالعه'), findsOneWidget);
    expect(find.text('156 تست'), findsOneWidget);
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

  testWidgets('dashboard task updates preserve v15-shaped reports and profile', (
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
    expect(stored['studentTrack'], legacyData['studentTrack']);
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
    expect(charts[0].days.map((day) => day.value), [0, 0, 0, 0, 0, 0, 270]);
    expect(charts[1].days.map((day) => day.value), [0, 0, 0, 0, 0, 0, 156]);
  });

  testWidgets(
    'planner opens a linked study report and saves it with its task',
    (tester) async {
      await openApp(tester);
      await tester.tap(find.text('برنامه شخصی'));
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
        (stored['reports'] as List).skip(1),
        legacyData['reports'],
      );
    },
  );
}
