import 'package:flutter/material.dart';

abstract final class AppColors {
  static const primary = Color(0xFF245FB5);
  static const deepBlue = Color(0xFF173F78);
  static const sky = Color(0xFFEAF3FF);
  static const canvas = Color(0xFFF7F9FC);
  static const ink = Color(0xFF202B3C);
  static const muted = Color(0xFF68758A);
  static const warm = Color(0xFFF2B85B);
  static const success = Color(0xFF23865B);
  static const border = Color(0xFFE7ECF3);
}

abstract final class AppTheme {
  static ThemeData get light {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      brightness: Brightness.light,
      surface: Colors.white,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme.copyWith(
        primary: AppColors.primary,
        secondary: AppColors.warm,
        surface: Colors.white,
      ),
      scaffoldBackgroundColor: AppColors.canvas,
      fontFamily: 'Vazirmatn',
      textTheme: const TextTheme(
        headlineSmall: TextStyle(fontSize: 23, fontWeight: FontWeight.w800, color: AppColors.ink, height: 1.5),
        titleLarge: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppColors.ink),
        titleMedium: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.ink),
        bodyLarge: TextStyle(fontSize: 15, color: AppColors.ink, height: 1.7),
        bodyMedium: TextStyle(fontSize: 13, color: AppColors.muted, height: 1.7),
        labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
      ),
      cardTheme: CardTheme(
        color: Colors.white,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: AppColors.border),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          minimumSize: const Size(48, 50),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        indicatorColor: AppColors.sky,
        height: 72,
        labelTextStyle: WidgetStateProperty.all(
          const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
