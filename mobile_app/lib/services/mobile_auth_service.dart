import 'study_activity_store.dart';
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

class MobileAuthService {
  factory MobileAuthService({http.Client? client}) =>
      client == null ? _shared : MobileAuthService._(client);

  MobileAuthService._(this._client);
  static final _shared = MobileAuthService._(http.Client());
  static const String _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
  );
  static const _storage = FlutterSecureStorage();
  final http.Client _client;
  static const isLocalTest =
      kDebugMode && bool.fromEnvironment('APEX_LOCAL_TEST');
  static const _localUrl = 'http://127.0.0.1:8765';
  Future<bool>? _refreshing;
  bool _loggingOut = false;
  int _sessionGeneration = 0;

  String get _endpoint => isLocalTest
      ? _localUrl
      : _baseUrl.replaceFirst(RegExp(r'/$'), '');
  String _key(String key) => isLocalTest ? 'apex_local_$key' : key;
  String _planKey(int id) => _key('study_plan_v1_$id');
  String _counselorKey(int id) => _key('counselor_context_v1_$id');
  bool get isConfigured {
    final uri = Uri.tryParse(_endpoint);
    return isLocalTest ||
        (uri != null && uri.scheme == 'https' &&
            uri.host.isNotEmpty && uri.userInfo.isEmpty && !uri.hasQuery &&
            !uri.hasFragment && (uri.path.isEmpty || uri.path == '/'));
  }

  Future<http.Response> _request(Uri uri, {
    required String method,
    Map<String, String>? headers,
    String? body,
  }) async {
    final request = http.Request(method, uri)..followRedirects = false;
    if (headers != null) request.headers.addAll(headers);
    if (body != null) request.body = body;
    return http.Response.fromStream(await _client.send(request));
  }

  Future<http.Response> _get(Uri uri, {Map<String, String>? headers}) =>
      _request(uri, method: 'GET', headers: headers);

  Future<http.Response> _post(Uri uri, {Map<String, String>? headers, String? body}) =>
      _request(uri, method: 'POST', headers: headers, body: body);

  Future<String?> _read(String key) => _storage.read(key: _key(key));

  Future<void> _saveSession(Map<String, dynamic> tokens) async {
    await _storage.write(
        key: _key('mobile_access_token'), value: tokens['access_token'] as String);
    await _storage.write(
        key: _key('mobile_refresh_token'), value: tokens['refresh_token'] as String);
  }

  Future<void> loginLocally(String code) async {
    if (!isLocalTest) throw StateError('ورود آزمایشی فعال نیست.');
    final response = await _post(
      Uri.parse('$_endpoint/api/v1/mobile/auth/local'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'code': code}),
    ).timeout(const Duration(seconds: 8));
    if (response.statusCode != 200) throw Exception('کد ورود آزمایشی پذیرفته نشد.');
    await clearSession();
    await _saveSession(jsonDecode(response.body) as Map<String, dynamic>);
    await fetchStudentProfile();
  }

  Future<void> clearSession() async {
    _sessionGeneration++;
    final id = await cachedStudentId();
    if (id != null) {
      await _storage.delete(key: _planKey(id));
      await _storage.delete(key: _counselorKey(id));
    }
    await _storage.delete(key: _key('mobile_access_token'));
    await _storage.delete(key: _key('mobile_refresh_token'));
    await _storage.delete(key: _key('cached_student_id'));
  }

  /// Revoke the server session before clearing local credentials.
  /// If offline, credentials are cleared locally; the remote session expires later.
  Future<void> logout() async {
    _loggingOut = true;
    _sessionGeneration++;
    try {
      // Wait for a rotating session to finish before revoking its new tokens.
      try {
        await _refreshing;
      } on Exception {
        // Logout still clears local credentials when refresh is unavailable.
      }
      final access = await _read('mobile_access_token');
      final refresh = await _read('mobile_refresh_token');
      if (access != null && refresh != null) {
        await _post(
          Uri.parse('$_endpoint/api/v1/mobile/auth/logout'),
          headers: {
            'Authorization': 'Bearer $access',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({'refresh_token': refresh}),
        ).timeout(const Duration(seconds: 8));
      }
    } catch (_) {
      // Local logout must work offline. The server token expires on its own.
    } finally {
      try {
        await clearSession();
      } finally {
        _loggingOut = false;
      }
    }
  }

  Future<bool> restoreSession() async {
    try {
      return await _refreshSession();
    } on Exception {
      // Keep the previously authenticated account available during outages.
      return await _read('mobile_refresh_token') != null &&
          await cachedStudentId() != null;
    }
  }

  Future<bool> _refreshSession() =>
      _refreshing ??= _rotateSession().whenComplete(() => _refreshing = null);

  Future<bool> _rotateSession() async {
    if (!isConfigured) return false;
    final refresh = await _read('mobile_refresh_token');
    if (refresh == null) return false;
    final response = await _post(
      Uri.parse('$_endpoint/api/v1/mobile/auth/refresh'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh_token': refresh}),
    ).timeout(const Duration(seconds: 8));
    if (response.statusCode == 401 || response.statusCode == 403) {
      await clearSession();
      return false;
    }
    if (response.statusCode != 200) {
      throw http.ClientException('Session refresh unavailable');
    }
    await _saveSession(jsonDecode(response.body) as Map<String, dynamic>);
    return true;
  }

  Future<http.Response> _authenticatedRequest(
      Future<http.Response> Function(String) send, {int? studentId}) async {
    final generation = _sessionGeneration;
    Future<http.Response> sendForCurrentSession(String token) async {
      final validStudent = studentId == null || await cachedStudentId() == studentId;
      if (!validStudent || _loggingOut || generation != _sessionGeneration) {
        throw StateError('حساب دانش‌آموز تغییر کرده است.');
      }
      final response = await send(token);
      if (_loggingOut || generation != _sessionGeneration) {
        throw StateError('حساب دانش‌آموز تغییر کرده است.');
      }
      return response;
    }
    if (!isConfigured) throw StateError('نشانی سرور امن تنظیم نشده است.');
    final access = await _read('mobile_access_token');
    if (access == null) throw StateError('ابتدا وارد حساب خود شوید.');
    final response = await sendForCurrentSession(access);
    if (response.statusCode != 401) return response;
    // A concurrent request may already have rotated this access token.
    final current = await _read('mobile_access_token');
    if (_loggingOut || generation != _sessionGeneration) {
      throw StateError('حساب دانش‌آموز تغییر کرده است.');
    }
    if (current == access && !await _refreshSession()) {
      throw StateError('نشست منقضی شده است. دوباره وارد شوید.');
    }
    final refreshed = await _read('mobile_access_token');
    if (refreshed == null) throw StateError('دوباره وارد شوید.');
    return sendForCurrentSession(refreshed);
  }

  Future<http.Response> _studentGet(String resource, {int? studentId}) => _authenticatedRequest(
        (token) => _get(
          Uri.parse('$_endpoint/api/v1/mobile/student/$resource'),
          headers: {'Authorization': 'Bearer $token'},
        ).timeout(const Duration(seconds: 8)),
        studentId: studentId,
      );

  Future<Map<String, dynamic>?> cachedCounselor(int studentId) async {
    final raw = await _storage.read(key: _counselorKey(studentId));
    return raw == null ? null : jsonDecode(raw) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> fetchCounselor(int studentId) async {
    final response = await _studentGet('counselor', studentId: studentId);
    if (response.statusCode != 200 || await cachedStudentId() != studentId) {
      throw StateError('دریافت اطلاعات مشاور ممکن نشد.');
    }
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    if (!data.containsKey('assignment') || !data.containsKey('plan')) {
      throw const FormatException('Invalid counselor response');
    }
    await _storage.write(key: _counselorKey(studentId), value: jsonEncode(data));
    return data;
  }

  Future<Map<String, dynamic>> confirmPlan(int studentId, int planId) async {
    final response = await _authenticatedRequest(
      (token) => _post(
        Uri.parse('$_endpoint/api/v1/mobile/student/counselor/plans/$planId/receipt'),
        headers: {'Authorization': 'Bearer $token'},
      ).timeout(const Duration(seconds: 8)),
      studentId: studentId,
    );
    if (response.statusCode != 200) {
      throw StateError('تأیید دریافت برنامه ممکن نشد.');
    }
    return fetchCounselor(studentId);
  }

  Future<List<Map<String, dynamic>>> fetchReportFeedback(int studentId) async {
    final response = await _studentGet('study-activities/feedback', studentId: studentId);
    if (response.statusCode != 200) {
      throw StateError('دریافت بازخورد ممکن نشد.');
    }
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return (body['feedback'] as List<dynamic>).cast<Map<String, dynamic>>();
  }

  Future<int?> cachedStudentId() async {
    final id = await _storage.read(key: _key('cached_student_id'));
    return id == null ? null : int.tryParse(id);
  }

  /// Fetches only the currently authenticated student's profile.
  /// Refreshes expired access credentials once; never accepts a student ID.
  Future<Map<String, dynamic>> fetchStudentProfile() async {
    final response = await _studentGet('profile');
    if (response.statusCode != 200) {
      throw Exception('دریافت مشخصات حساب ممکن نشد. دوباره تلاش کنید.');
    }
    final profile = jsonDecode(response.body) as Map<String, dynamic>;
    final id = (profile['student_id'] as num).toInt();
    await _storage.write(key: _key('cached_student_id'), value: id.toString());
    return profile;
  }

  /// Send pending activities in batches, acknowledging only IDs confirmed by server.
  Future<int> syncStudyActivities(int studentId, StudyActivityStore store) async {
    if (await cachedStudentId() != studentId) {
      throw StateError('شناسه حساب با گزارش‌های محلی مطابقت ندارد.');
    }
    final pending = (await store.read(studentId))
        .where((a) => a['sync_state'] != 'synced').toList();
    var synced = 0;
    for (var offset = 0; offset < pending.length; offset += 50) {
      final batch = pending.skip(offset).take(50).toList();
      Future<http.Response> send(String token) => _post(
        Uri.parse('$_endpoint/api/v1/mobile/student/study-activities/sync'),
        headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
        body: jsonEncode({'activities': batch}),
      ).timeout(const Duration(seconds: 20));
      final response = await _authenticatedRequest(send, studentId: studentId);
      if (response.statusCode != 200) {
        throw StateError('همگام‌سازی انجام نشد (کد ${response.statusCode}). گزارش‌ها روی گوشی باقی می‌مانند.');
      }
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final ids = (body['accepted_event_ids'] as List<dynamic>).cast<String>();
      final expected = batch.map((e) => e['event_id'] as String).toSet();
      if (ids.length != expected.length || ids.toSet().length != expected.length || !expected.containsAll(ids)) {
        throw StateError('تأیید سرور با گزارش‌های ارسالی مطابقت ندارد.');
      }
      await store.markSynced(studentId, ids);
      synced += ids.length;
    }
    return synced;
  }

  static const _botUsername = 'TaranomHamDeliBot';

  Future<void> openRegistration() async {
    final uri = Uri.https('t.me', '/$_botUsername', {'start': 'apex360'});
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      throw StateError('باز کردن ربات ثبت‌نام ممکن نشد.');
    }
  }

  Future<void> checkCentralWorkflow() async {
    if (!isConfigured || isLocalTest) {
      throw StateError('نشانی HTTPS سامانه مرکزی برای این ساخت تنظیم نشده است.');
    }
    final response = await _get(Uri.parse('$_endpoint/api/v1/mobile/capabilities'))
        .timeout(const Duration(seconds: 8));
    if (response.statusCode != 200) {
      throw StateError('قرارداد اتصال در سامانه در دسترس نیست (کد ${response.statusCode}).');
    }
    final data = jsonDecode(response.body);
    if (data is! Map || data['api_version'] != 1 ||
        data['student_workflow_version'] != 17 ||
        data['authentication'] != 'telegram-deep-link-approval' ||
        data['counselor_assignment'] != true || data['plan_receipts'] != true ||
        data['report_feedback'] != true) {
      throw StateError('سامانه هنوز چرخهٔ دانش‌آموز و مشاور نسخهٔ ۱۷ را اعلام نکرده است.');
    }
  }

  Future<void> loginWithTelegram({required void Function(String) onStatus}) async {
    onStatus('در حال بررسی اتصال به سامانهٔ مرکزی…');
    await checkCentralWorkflow();
    onStatus('در حال ساخت درخواست ورود امن…');
    final created = await _post(
      Uri.parse('$_endpoint/api/v1/mobile/auth/challenge'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'platform': 'flutter'}),
    ).timeout(const Duration(seconds: 8));
    if (created.statusCode == 404) {
      throw Exception('قابلیت ورود اپ هنوز روی سرور فعال نشده است. لطفاً منتظر نسخه متصل به سرور آزمایشی باشید.');
    }
    if (created.statusCode == 502 || created.statusCode == 503 || created.statusCode == 504) {
      throw Exception('سرور موقتاً در دسترس نیست. کمی بعد دوباره امتحان کنید.');
    }
    if (created.statusCode != 200) {
      throw Exception('ساخت درخواست ورود ناموفق بود (کد ${created.statusCode}).');
    }
    final challenge = jsonDecode(created.body) as Map<String, dynamic>;
    final challengeId = challenge['challenge_id'] as String;
    final verificationUrl = Uri.parse(challenge['verification_url'] as String);
    if (verificationUrl.scheme != 'https' || verificationUrl.host != 't.me' ||
        verificationUrl.userInfo.isNotEmpty || verificationUrl.port != 443 ||
        verificationUrl.hasFragment || verificationUrl.path != '/$_botUsername' ||
        verificationUrl.queryParametersAll.length != 1 ||
        verificationUrl.queryParametersAll['start']?.length != 1) {
      throw Exception('پیوند تأیید ورود معتبر نیست.');
    }
    final start = verificationUrl.queryParameters['start'];
    if (start == null) throw Exception('پیوند تأیید ورود معتبر نیست.');
    final parts = start.split('_');
    if (parts.length != 3 || parts[0] != 'mobile' || parts[1] != challengeId ||
        !RegExp(r'^[a-f0-9]{12}$').hasMatch(challengeId) ||
        !RegExp(r'^[a-f0-9]{32}$').hasMatch(parts[2])) throw Exception('شناسه درخواست ورود معتبر نیست.');
    final secret = parts[2];

    onStatus('در تلگرام، ورود به اپلیکیشن را تأیید کنید.');
    final launched = await launchUrl(verificationUrl, mode: LaunchMode.externalApplication);
    if (!launched) throw Exception('باز کردن تلگرام ممکن نشد.');
    final expiry = DateTime.now().add(Duration(seconds: (challenge['expires_in'] as num).toInt()));
    while (DateTime.now().isBefore(expiry)) {
      await Future<void>.delayed(Duration(seconds: (challenge['poll_interval_seconds'] as num).toInt()));
      final response = await _post(
        Uri.parse('$_endpoint/api/v1/mobile/auth/challenge/$challengeId'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'secret': secret}),
      ).timeout(const Duration(seconds: 8));
      if (response.statusCode != 200) throw Exception('بررسی وضعیت ورود ناموفق بود.');
      final result = jsonDecode(response.body) as Map<String, dynamic>;
      if (result['status'] == 'authenticated') {
        await clearSession();
        await _saveSession(result);
        await fetchStudentProfile();
        onStatus('ورود با موفقیت تأیید شد.');
        return;
      }
      if (result['status'] == 'expired') throw Exception('مهلت ورود تمام شد. دوباره تلاش کنید.');
      if (result['status'] == 'consumed') throw Exception('این درخواست قبلاً استفاده شده است.');
      onStatus('منتظر تأیید شما در ربات تلگرام هستیم...');
    }
    throw Exception('زمان تأیید ورود به پایان رسید. دوباره تلاش کنید.');
  }
}
