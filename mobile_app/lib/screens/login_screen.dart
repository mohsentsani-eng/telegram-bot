import 'package:flutter/material.dart';

import '../services/mobile_auth_service.dart';
import '../theme/app_theme.dart';
import 'apex_dashboard.dart';
import 'apex_demo_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onAuthenticated});

  final VoidCallback onAuthenticated;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _auth = MobileAuthService();
  final _code = TextEditingController();
  static const _local = MobileAuthService.isLocalTest;

  bool _busy = false;
  String? _status;
  String? _error;

  Future<void> _login() async {
    if (_busy) return;
    if (_local && _code.text.trim().isEmpty) {
      setState(() => _error = 'کد ورود آزمایشی را وارد کن.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _status = 'در حال آماده‌سازی ورود…';
    });
    try {
      if (_local) {
        await _auth.loginLocally(_code.text.trim());
      } else {
        await _auth.loginWithTelegram(onStatus: (message) {
          if (mounted) setState(() => _status = message);
        });
      }
      if (mounted) widget.onAuthenticated();
    } catch (error) {
      if (mounted) setState(() {
        _error = switch (error) {
          StateError(:final message) => message,
          _ when error.toString().startsWith('Exception: ') =>
            error.toString().substring('Exception: '.length),
          _ => 'برقراری ارتباط ممکن نشد. اتصال را بررسی کن.',
        };
      });
    } finally {
      if (mounted) setState(() {
        _busy = false;
        _status = null;
      });
    }
  }

  Future<void> _register() async {
    try {
      await _auth.openRegistration();
    } catch (_) {
      if (mounted) setState(() => _error = 'ربات ثبت‌نام باز نشد.');
    }
  }

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 440),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        gradient: AppColors.apexGradient,
                        borderRadius: BorderRadius.circular(28),
                      ),
                      child: const Row(children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Apex360',
                                  style: TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900)),
                              Text('همراه مطالعهٔ ترنم همدلی',
                                  style: TextStyle(color: AppColors.mint, height: 1.7)),
                            ],
                          ),
                        ),
                        SizedBox(width: 12),
                        AvaCompanion(celebrating: false),
                      ]),
                    ),
                    const SizedBox(height: 14),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Text(_local ? 'ورود آزمایشی همایش' : 'ورود دانش‌آموز به سامانهٔ ترنم همدلی',
                                style: theme.textTheme.titleLarge),
                            const SizedBox(height: 4),
                            Text(_local
                                ? 'این نسخه به سرور محلی نمایش وصل می‌شود. کد حساب ساختگی را وارد کن.'
                                : 'با همان حساب تلگرامی وارد شو که با آن ثبت‌نام کردی.'),
                            const SizedBox(height: 14),
                            if (_local) ...[
                              TextField(
                                controller: _code,
                                obscureText: true,
                                autocorrect: false,
                                enabled: !_busy,
                                textInputAction: TextInputAction.go,
                                onSubmitted: (_) => _login(),
                                decoration: const InputDecoration(labelText: 'کد ورود آزمایشی'),
                              ),
                              const SizedBox(height: 10),
                            ],
                            if (_status != null) Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: Semantics(liveRegion: true, child: Text(_status!)),
                            ),
                            if (_error != null) Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: Semantics(
                                liveRegion: true,
                                child: Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
                              ),
                            ),
                            FilledButton.icon(
                              onPressed: _busy ? null : _login,
                              icon: const Icon(Icons.lock_open_rounded),
                              label: Text(_busy ? 'در حال ورود…' : (_local ? 'ورود آزمایشی' : 'ورود با تلگرام')),
                            ),
                            if (!_local)
                              TextButton.icon(
                                onPressed: _busy ? null : _register,
                                icon: const Icon(Icons.person_add_alt_rounded),
                                label: const Text('ثبت‌نام در ربات ترنم همدلی'),
                              ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    TextButton.icon(
                      onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => const ApexDemoScreen(),
                      )),
                      icon: const Icon(Icons.phone_android_rounded),
                      label: const Text('باز کردن داشبورد آفلاین'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
