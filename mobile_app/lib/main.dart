import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'screens/student_home_screen.dart';
import 'services/mobile_auth_service.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const TaranomApp());
}

class TaranomApp extends StatelessWidget {
  const TaranomApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ترنم همدلی',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      locale: const Locale('fa'),
      home: const _AuthenticationGate(),
    );
  }
}

class _AuthenticationGate extends StatefulWidget {
  const _AuthenticationGate();

  @override
  State<_AuthenticationGate> createState() => _AuthenticationGateState();
}

class _AuthenticationGateState extends State<_AuthenticationGate> {
  final _auth = MobileAuthService();
  bool? _authenticated;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    final valid = await _auth.restoreSession();
    if (mounted) setState(() => _authenticated = valid);
  }

  void _onAuthenticated() => setState(() => _authenticated = true);

  @override
  Widget build(BuildContext context) {
    if (_authenticated == null) {
      return const Directionality(
        textDirection: TextDirection.rtl,
        child: Scaffold(body: Center(child: CircularProgressIndicator())),
      );
    }
    if (!_authenticated!) {
      return LoginScreen(onAuthenticated: _onAuthenticated);
    }
    return const StudentHomeScreen();
  }
}
