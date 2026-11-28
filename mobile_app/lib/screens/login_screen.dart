import 'package:flutter/material.dart';

import '../services/mobile_auth_service.dart';
import '../theme/app_theme.dart';
import '../theme/apex_components.dart';
import 'apex_dashboard.dart';
import 'apex_demo_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.onAuthenticated,
    this.onThemeChanged,
  });
  final ValueChanged<bool>? onThemeChanged;

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
        await _auth.loginWithTelegram(
          onStatus: (message) {
            if (mounted) setState(() => _status = message);
          },
        );
      }
      if (mounted) widget.onAuthenticated();
    } catch (error) {
      if (mounted)
        setState(() {
          _error = switch (error) {
            StateError(:final message) => message,
            _ when error.toString().startsWith('Exception: ') =>
              error.toString().substring('Exception: '.length),
            _ => 'برقراری ارتباط ممکن نشد. اتصال را بررسی کن.',
          };
        });
    } finally {
      if (mounted)
        setState(() {
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
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: ListView(
                shrinkWrap: true,
                padding: const EdgeInsets.all(20),
                children: [
                  Container(
                    padding: const EdgeInsets.fromLTRB(20, 14, 20, 22),
                    decoration: BoxDecoration(
                      color: AppColors.night,
                      borderRadius: BorderRadius.circular(32),
                    ),
                    child: const Column(
                      children: [
                        AvaCompanion(celebrating: false, size: 132),
                        Text(
                          'Apex360',
                          textDirection: TextDirection.ltr,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 36,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Text(
                          'آوا، همراه مطالعهٔ تو',
                          style: TextStyle(color: AppColors.mint, fontSize: 16),
                        ),
                      ],
                    ),
                  ),
                  ApexSection(
                    _local ? 'ورود آزمایشی همایش' : 'ورود به حساب دانش‌آموز',
                    detail: _local ? 'کد حساب ساختگی را وارد کن.' : 'ورود از طریق همان حساب تلگرام که با آن ثبت‌نام کردی.',
                  ),
                  if (_local)
                    TextField(
                      controller: _code,
                      obscureText: true,
                      autocorrect: false,
                      enabled: !_busy,
                      textInputAction: TextInputAction.go,
                      onSubmitted: (_) => _login(),
                      decoration: const InputDecoration(
                        labelText: 'کد ورود آزمایشی',
                      ),
                    ),
                  if (_status != null) ...[
                    const LinearProgressIndicator(),
                    Semantics(liveRegion: true, child: Text(_status!)),
                  ],
                  if (_error != null)
                    Semantics(
                      liveRegion: true,
                      child: Text(
                        _error!,
                        style: TextStyle(color: theme.colorScheme.error),
                      ),
                    ),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    onPressed: _busy ? null : _login,
                    icon: const Icon(Icons.lock_outline),
                    label: Text(
                      _busy
                          ? 'در حال ورود…'
                          : (_local ? 'ورود آزمایشی' : 'ورود با تلگرام'),
                    ),
                  ),
                  if (!_local)
                    TextButton(
                      onPressed: _busy ? null : _register,
                      child: const Text('ثبت‌نام در ربات ترنم همدلی'),
                    ),
                  const SizedBox(height: 8),
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.phone_android_rounded),
                      title: const Text('باز کردن داشبورد آفلاین'),
                      subtitle: const Text('برنامه و گزارش شخصی روی همین گوشی'),
                      trailing: const Icon(Icons.chevron_left),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => ApexDemoScreen(
                            onThemeChanged: widget.onThemeChanged,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
