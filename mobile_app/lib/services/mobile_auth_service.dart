import 'dart:async';
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

class MobileAuthService {
  MobileAuthService({http.Client? client}) : _client = client ?? http.Client();
  static const String _baseUrl = String.fromEnvironment(
    'API_BASE_URL', defaultValue: 'https://YOUR-RAILWAY-DOMAIN',
  );
  static const _storage = FlutterSecureStorage();
  final http.Client _client;
  bool get isConfigured => !_baseUrl.contains('YOUR-RAILWAY-DOMAIN');

  Future<void> clearSession() async {
    await _storage.delete(key: 'mobile_access_token');
    await _storage.delete(key: 'mobile_refresh_token');
  }

  Future<void> loginWithTelegram({required void Function(String) onStatus}) async {
    if (!isConfigured) throw Exception('نشانی امن سرور هنوز در نسخه آزمایشی تنظیم نشده است.');
    onStatus('در حال ساخت درخواست ورود امن...');
    final created = await _client.post(
      Uri.parse('$_baseUrl/api/v1/mobile/auth/challenge'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'platform': 'flutter'}),
    );
    if (created.statusCode != 200) throw Exception('ساخت درخواست ورود ناموفق بود.');
    final challenge = jsonDecode(created.body) as Map<String, dynamic>;
    final challengeId = challenge['challenge_id'] as String;
    final verificationUrl = Uri.parse(challenge['verification_url'] as String);
    final start = verificationUrl.queryParameters['start'];
    if (start == null) throw Exception('پیوند تأیید ورود معتبر نیست.');
    final parts = start.split('_');
    if (parts.length != 3) throw Exception('شناسه درخواست ورود معتبر نیست.');
    final secret = parts[2];

    onStatus('در تلگرام، ورود به اپلیکیشن را تأیید کنید.');
    final launched = await launchUrl(verificationUrl, mode: LaunchMode.externalApplication);
    if (!launched) throw Exception('باز کردن تلگرام ممکن نشد.');
    final expiry = DateTime.now().add(Duration(seconds: (challenge['expires_in'] as num).toInt()));
    while (DateTime.now().isBefore(expiry)) {
      await Future<void>.delayed(Duration(seconds: (challenge['poll_interval_seconds'] as num).toInt()));
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/mobile/auth/challenge/$challengeId')
            .replace(queryParameters: {'secret': secret}),
      );
      if (response.statusCode != 200) throw Exception('بررسی وضعیت ورود ناموفق بود.');
      final result = jsonDecode(response.body) as Map<String, dynamic>;
      if (result['status'] == 'authenticated') {
        await _storage.write(key: 'mobile_access_token', value: result['access_token'] as String);
        await _storage.write(key: 'mobile_refresh_token', value: result['refresh_token'] as String);
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
