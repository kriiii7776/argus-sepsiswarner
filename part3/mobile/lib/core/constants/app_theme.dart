import 'package:flutter/material.dart';

class AppColors {
  static const Color redUrgent = Color(0xFFD32F2F);
  static const Color redUrgentBg = Color(0xFFFFEBEE);
  static const Color orangeReview = Color(0xFFE65100);
  static const Color orangeReviewBg = Color(0xFFFFF3E0);
  static const Color yellowWatch = Color(0xFFF57F17);
  static const Color yellowWatchBg = Color(0xFFFFFDE7);
  static const Color greenNormal = Color(0xFF2E7D32);
  static const Color greenNormalBg = Color(0xE8E8F5E9);

  static const Color connectedGreen = Color(0xFF4CAF50);
  static const Color reconnectingAmber = Color(0xFFFF9800);
  static const Color disconnectedRed = Color(0xFFF44336);

  static const Color cardBackground = Color(0xFF1E1E2C);
  static const Color surfaceDark = Color(0xFF12121D);
}

class AppTheme {
  static ThemeData darkTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: const Color(0xFF0F0F18),
    colorScheme: const ColorScheme.dark(
      primary: Color(0xFF64B5F6),
      surface: Color(0xFF1E1E2C),
    ),
    cardTheme: CardThemeData(
      color: const Color(0xFF1E1E2C),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xFF12121D),
      elevation: 0,
      centerTitle: false,
    ),
  );
}
