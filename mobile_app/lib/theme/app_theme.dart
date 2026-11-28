import 'package:flutter/material.dart';

abstract final class AppColors {
  static const primary = Color(0xFF006957);
  static const muted = Color(0xFF465A57);
  static const success = Color(0xFF18724C);
  static const mint = Color(0xFFBDF6E3);
  static const night = Color(0xFF112C38);
}

abstract final class AppTheme {
  static ThemeData get light => build(Brightness.light);
  static ThemeData get dark => build(Brightness.dark);

  static ThemeData build(Brightness brightness) {
    final dark = brightness == Brightness.dark;
    final violet = ColorScheme.fromSeed(
        seedColor: const Color(0xFF6549A7), brightness: brightness);
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      brightness: brightness,
      dynamicSchemeVariant: DynamicSchemeVariant.fidelity,
    ).copyWith(
      secondaryContainer: violet.primaryContainer,
      onSecondaryContainer: violet.onPrimaryContainer,
      tertiaryContainer: Color(dark ? 0xFF523C16 : 0xFFFFE4A8),
      onTertiaryContainer: Color(dark ? 0xFFFFE4A8 : 0xFF332305),
    );
    return ThemeData(
      colorScheme: scheme,
      fontFamily: 'Vazirmatn',
      scaffoldBackgroundColor: scheme.surface,
      appBarTheme: AppBarTheme(
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        scrolledUnderElevation: 0,
      ),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(
          fontSize: 25,
          fontWeight: FontWeight.w700,
          height: 1.42,
        ),
        titleLarge: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          height: 1.45,
        ),
        titleMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        bodyLarge: TextStyle(fontSize: 16, height: 1.55),
        bodyMedium: TextStyle(fontSize: 14, height: 1.55),
        labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        labelSmall: TextStyle(fontSize: 12),
      ),
      cardTheme: CardThemeData(
        color: scheme.surfaceContainerLow,
        elevation: 0,
        margin: const EdgeInsets.only(bottom: 8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
          side: BorderSide(color: scheme.outlineVariant),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(48, 50),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surfaceContainerHighest,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: scheme.surfaceContainerLow,
        indicatorColor: scheme.primaryContainer,
        height: 68,
        labelTextStyle: WidgetStateProperty.all(
          const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}
