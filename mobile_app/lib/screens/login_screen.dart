import 'package:flutter/material.dart';
import '../services/mobile_auth_service.dart';
import '../theme/app_theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onAuthenticated});
  final VoidCallback onAuthenticated;
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _auth = MobileAuthService();
  bool _busy = false;
  String _status = 'برای اتصال امن به پرونده دانش‌آموزی، با تلگرام وارد شوید.';
  String? _error;

  Future<void> _login() async {
    setState(() { _busy = true; _error = null; _status = 'در حال آماده‌سازی ورود...'; });
    try {
      await _auth.loginWithTelegram(onStatus: (message) {
        if (mounted) setState(() => _status = message);
      });
      if (mounted) widget.onAuthenticated();
    } catch (error) {
      if (mounted) setState(() {
        _error = error.toString().replaceFirst('Exception: ', '');
        _status = 'ورود تکمیل نشد.';
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
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
            Container(height: 76, alignment: Alignment.center,
              decoration: BoxDecoration(color: AppColors.sky, borderRadius: BorderRadius.circular(24)),
              child: const Icon(Icons.spa_rounded, color: AppColors.primary, size: 42)),
            const SizedBox(height: 22),
            const Text('به ترنم همدلی خوش آمدید', textAlign: TextAlign.center,
              style: TextStyle(fontSize: 23, fontWeight: FontWeight.w900, color: AppColors.deepBlue)),
            const SizedBox(height: 9),
            const Text('ورود امن به همراهی تحصیلی و مسیر حال خوب', textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: AppColors.muted)),
            const SizedBox(height: 34),
            Card(child: Padding(padding: const EdgeInsets.all(20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                const Icon(Icons.telegram_rounded, size: 42, color: AppColors.primary),
                const SizedBox(height: 14),
                const Text('ورود با حساب تلگرام', textAlign: TextAlign.center,
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
                FilledButton.icon(
                  onPressed: _busy ? null : _login,
                  icon: _busy ? const SizedBox(width: 18, height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.lock_open_rounded),
                  label: Text(_busy ? 'در انتظار تأیید...' : 'ورود با تلگرام'),
                  style: FilledButton.styleFrom(backgroundColor: AppColors.primary, minimumSize: const Size.fromHeight(52)),
                ),
              ]))),
            const SizedBox(height: 18),
            const Text('برای ورود، باید با همین حساب تلگرام در ربات رسمی ترنم همدلی پرونده دانش‌آموزی داشته باشید.',
              textAlign: TextAlign.center, style: TextStyle(fontSize: 11, height: 1.8, color: AppColors.muted)),
          ]),
        ),
      ))),
    ),
  );
}
