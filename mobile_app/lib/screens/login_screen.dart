import 'package:flutter/material.dart';
import '../services/mobile_auth_service.dart';
import 'apex_demo_screen.dart';
import '../theme/app_theme.dart';

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
  String _status = _local ? 'کد چاپ‌شده در API محلی را وارد کنید.' : 'برای اتصال امن به پرونده دانش‌آموزی، با تلگرام وارد شوید.';
  String? _error;

  Future<void> _login() async {
    setState(() { _busy = true; _error = null; _status = 'در حال آماده‌سازی ورود...'; });
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
        _error = error is StateError || error.toString().startsWith('Exception: ')
            ? error.toString().replaceFirst('Exception: ', '').replaceFirst('Bad state: ', '')
            : 'برقراری ارتباط ممکن نشد. اتصال را بررسی کنید.';
        _status = 'ورود تکمیل نشد.';
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Directionality(
    textDirection: TextDirection.rtl,
    child: Scaffold(
      body: SafeArea(child: Center(child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 420),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                gradient: AppColors.apexGradient,
                borderRadius: BorderRadius.circular(28),
              ),
              child: const Column(children: [
                Icon(Icons.auto_awesome_rounded, color: Color(0xFFAAEEE2), size: 36),
                SizedBox(height: 10),
                Text('Apex360', style: TextStyle(color: Colors.white, fontSize: 31,
                  fontWeight: FontWeight.w900)),
                Text('ترنم همدلی', style: TextStyle(color: Colors.white)),
              ]),
            ),
            const SizedBox(height: 34),
            Card(child: Padding(padding: const EdgeInsets.all(20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                const Icon(Icons.lock_outline_rounded, size: 34, color: AppColors.primary),
                const SizedBox(height: 14),
                const Text(_local ? 'ورود دانش‌آموز آزمایشی' : 'ورود با حساب تلگرام', textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: AppColors.ink)),
                const SizedBox(height: 10),
                Text(_status, textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 12, height: 1.8, color: AppColors.muted)),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.red, fontSize: 12, height: 1.7)),
                ],
                const SizedBox(height: 20),
                if (_local)
                  TextField(
                    controller: _code,
                    obscureText: true,
                    autocorrect: false,
                    decoration: const InputDecoration(labelText: 'کد ورود آزمایشی'),
                  ),
                FilledButton.icon(
                  onPressed: _busy ? null : _login,
                  icon: _busy ? const SizedBox(width: 18, height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.lock_open_rounded),
                  label: Text(_busy ? 'در انتظار تأیید...' : (_local ? 'ورود آزمایشی' : 'ورود با تلگرام')),
                  style: FilledButton.styleFrom(backgroundColor: AppColors.primary, minimumSize: const Size.fromHeight(52)),
                ),
              ]))),
            const SizedBox(height: 18),
            if (!_local) const Text('برای ورود، باید با همین حساب تلگرام در ربات رسمی ترنم همدلی پرونده دانش‌آموزی داشته باشید.',
              textAlign: TextAlign.center, style: TextStyle(fontSize: 11, height: 1.8, color: AppColors.muted)),
            TextButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                builder: (_) => const ApexDemoScreen(),
              )),
              child: const Text('باز کردن داشبورد آفلاین'),
            ),
          ]),
        ),
      ))),
    ),
  );
}
