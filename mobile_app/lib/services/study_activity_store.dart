import 'dart:convert';
import 'dart:math';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Local encrypted queue of study activities. No server sync is claimed yet.
/// Data is scoped to the authenticated student and must never be shared across logins.
class StudyActivityStore {
  static const _storage = FlutterSecureStorage();
  static const _prefix = 'study_activities_v1_';

  Future<List<Map<String, dynamic>>> read(int studentId) async {
    final raw = await _storage.read(key: '$_prefix$studentId');
    if (raw == null || raw.isEmpty) return [];
    final decoded = jsonDecode(raw) as List<dynamic>;
    return decoded.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<void> markSynced(int studentId, List<String> acceptedIds) async {
    if (acceptedIds.isEmpty) return;
    final ids = acceptedIds.toSet();
    final activities = await read(studentId);
    for (final activity in activities) {
      if (ids.contains(activity['event_id'])) activity['sync_state'] = 'synced';
    }
    await _storage.write(key: '$_prefix$studentId', value: jsonEncode(activities));
  }

  Future<Map<String, dynamic>> add({
    required int studentId,
    required String subject,
    required String activityType,
    required int durationMinutes,
    required int testCount,
  }) async {
    final normalizedSubject = subject.trim();
    if (normalizedSubject.isEmpty || normalizedSubject.length > 80) {
      throw ArgumentError('نام درس باید بین ۱ تا ۸۰ نویسه باشد.');
    }
    if (durationMinutes < 1 || durationMinutes > 720) {
      throw ArgumentError('مدت مطالعه باید بین ۱ تا ۷۲۰ دقیقه باشد.');
    }
    if (testCount < 0 || testCount > 1000) {
      throw ArgumentError('تعداد تست نامعتبر است.');
    }
    const allowed = {'study', 'practice', 'review', 'video'};
    if (!allowed.contains(activityType)) throw ArgumentError('نوع فعالیت نامعتبر است.');
    final activities = await read(studentId);
    if (activities.length >= 200) {
      throw StateError('ظرفیت ثبت آفلاین تکمیل شده است. پیش از ثبت بیشتر باید همگام‌سازی فعال شود.');
    }
    final now = DateTime.now().toUtc();
    final random = Random.secure();
    final id = '${now.microsecondsSinceEpoch}-${List.generate(16, (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0')).join()}';
    final activity = <String, dynamic>{
      'event_id': id,
      'subject': normalizedSubject,
      'activity_type': activityType,
      'duration_minutes': durationMinutes,
      'test_count': testCount,
      'created_at': now.toIso8601String(),
      'sync_state': 'pending',
    };
    activities.insert(0, activity);
    await _storage.write(key: '$_prefix$studentId', value: jsonEncode(activities));
    return activity;
  }
}
