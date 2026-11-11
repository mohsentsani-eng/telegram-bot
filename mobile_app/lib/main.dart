import 'package:flutter/material.dart';
import 'screens/student_home_screen.dart';
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
      home: const StudentHomeScreen(),
    );
  }
}
