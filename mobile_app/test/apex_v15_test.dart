import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:taranom_hamdeli/main.dart';
import 'package:taranom_hamdeli/services/mobile_auth_service.dart';
import 'package:taranom_hamdeli/services/study_activity_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('reads the version from package metadata across navigation', (tester) async {
    PackageInfo.setMockInitialValues(
      appName: 'Apex360', packageName: 'ir.taranomhamdeli.taranom_hamdeli',
      version: '0.16.0', buildNumber: '44', buildSignature: '',
    );
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const TaranomApp());
    await tester.pumpAndSettle();
    expect(find.text('Apex360 · 0.16.0+44'), findsOneWidget);
    final offline = find.text('باز کردن داشبورد آفلاین');
    await tester.ensureVisible(offline);
    await tester.tap(offline);
    await tester.pumpAndSettle();
    expect(find.text('Apex360 · 0.16.0+44'), findsOneWidget);
    expect(find.text('ابتدا پروفایل خود را تکمیل کنید'), findsOneWidget);
  });

  test('keeps reports pending until matching server acknowledgment', () async {
    FlutterSecureStorage.setMockInitialValues({
      'mobile_access_token': 'access',
      'mobile_refresh_token': 'refresh',
      'cached_student_id': '14',
    });
    var online = true;
    var invalidAck = true;
    var noAssignment = false;
    final client = MockClient((request) async {
      expect(request.followRedirects, isFalse);
      if (!online) throw http.ClientException('disconnected');
      if (request.url.path.endsWith('/counselor')) {
        return http.Response(noAssignment
            ? '{"assignment":null,"plan":null}'
            : '{"assignment":{"id":1,"name":"مشاور"},"plan":{"id":2,"schedule":[]}}', 200,
            headers: {"content-type": "application/json"});
      }
      final activities = (jsonDecode(request.body) as Map)['activities'] as List;
      final id = (activities.single as Map)['event_id'];
      return http.Response(jsonEncode({
        'accepted_event_ids': [invalidAck ? 'unrelated-event' : id],
      }), 200);
    });
    final auth = MobileAuthService(client: client);
    final store = StudyActivityStore();
    expect((await auth.fetchCounselor(14))['plan']['id'], 2);
    online = false;
    expect(await MobileAuthService(client: client).restoreSession(), isTrue);
    expect((await auth.cachedCounselor(14))?['plan']['id'], 2);
    final event = await store.add(studentId: 14, subject: 'ریاضی',
        activityType: 'study', durationMinutes: 45, testCount: 5);
    await expectLater(auth.syncStudyActivities(14, store), throwsException);
    online = true;
    await expectLater(auth.syncStudyActivities(14, store), throwsStateError);
    expect((await StudyActivityStore().read(14)).single['sync_state'], 'pending');
    invalidAck = false;
    expect(await auth.syncStudyActivities(14, store), 1);
    final synced = (await store.read(14)).single;
    expect(synced['event_id'], event['event_id']);
    expect(synced['sync_state'], 'synced');
    noAssignment = true;
    await auth.fetchCounselor(14);
    expect((await auth.cachedCounselor(14))?['plan'], isNull);
  }, skip: const String.fromEnvironment('API_BASE_URL').isEmpty);
}
