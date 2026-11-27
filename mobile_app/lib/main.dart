import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'screens/login_screen.dart';
import 'screens/apex_demo_screen.dart';
import 'screens/student_home_screen.dart';
import 'services/mobile_auth_service.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const TaranomApp());
}

class TaranomApp extends StatefulWidget {
  const TaranomApp({super.key});

  @override
  State<TaranomApp> createState() => _TaranomAppState();
}

class _TaranomAppState extends State<TaranomApp> {
  final _package = PackageInfo.fromPlatform();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ترنم همدلی',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      locale: const Locale('fa'),
      builder: (context, navigator) => FutureBuilder<PackageInfo>(
        future: _package,
        builder: (context, snapshot) {
          final info = snapshot.data;
          final showVersion = info != null && info.version.isNotEmpty && info.buildNumber.isNotEmpty;
          final theme = Theme.of(context);
          return Column(
            children: [
              Expanded(child: MediaQuery.removePadding(
                context: context,
                removeBottom: showVersion,
                child: navigator!,
              )),
              if (showVersion) Material(
                color: theme.colorScheme.surface,
                child: SafeArea(
                  top: false,
                  child: Center(
                    child: Text(
                      'Apex360 · ${info.version}+${info.buildNumber}',
                      textDirection: TextDirection.ltr,
                      style: theme.textTheme.labelSmall,
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
      home: const bool.fromEnvironment('APEX_DEMO_MODE', defaultValue: false)
          ? const ApexDemoScreen()
          : const _AuthenticationGate(),
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

  void _onLoggedOut() => setState(() => _authenticated = false);

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
    return StudentHomeScreen(onLoggedOut: _onLoggedOut);
  }
}
