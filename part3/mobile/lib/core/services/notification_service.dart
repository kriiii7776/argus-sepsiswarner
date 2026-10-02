import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import '../utils/risk_formatter.dart';

typedef NotificationTapCallback = void Function(String patientId);

class NotificationService {
  static final NotificationService instance = NotificationService._internal();

  final FlutterLocalNotificationsPlugin _notificationsPlugin = FlutterLocalNotificationsPlugin();
  bool _isInitialized = false;
  NotificationTapCallback? onNotificationTap;

  // Alert Deduplication: track last notified alert severity per patient
  final Map<String, String> _lastNotifiedSeverity = {};

  factory NotificationService() {
    return instance;
  }

  NotificationService._internal();

  static const String channelId = 'argus_urgent_alerts';
  static const String channelName = 'ARGUS Urgent Clinical Alerts';
  static const String channelDescription = 'High-priority notifications for critical sepsis risk escalation';

  Future<void> initialize({NotificationTapCallback? onTap}) async {
    if (_isInitialized) return;
    onNotificationTap = onTap;

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidSettings);

    try {
      await _notificationsPlugin.initialize(
        initSettings,
        onDidReceiveNotificationResponse: (NotificationResponse response) {
          final payload = response.payload;
          if (payload != null && payload.isNotEmpty) {
            onNotificationTap?.call(payload);
          }
        },
      );

      await _createNotificationChannel();

      _isInitialized = true;
      await requestPermissions();
    } catch (e) {
      if (kDebugMode) {
        print('NotificationService initialization error: $e');
      }
    }
  }

  Future<void> _createNotificationChannel() async {
    try {
      final androidImplementation =
          _notificationsPlugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
      if (androidImplementation != null) {
        final vibrationPattern = Int64List.fromList([0, 500, 200, 500, 200, 500]);
        final channel = AndroidNotificationChannel(
          channelId,
          channelName,
          description: channelDescription,
          importance: Importance.max,
          playSound: true,
          enableVibration: true,
          vibrationPattern: vibrationPattern,
        );
        await androidImplementation.createNotificationChannel(channel);
      }
    } catch (e) {
      if (kDebugMode) {
        print('Error creating notification channel: $e');
      }
    }
  }

  Future<bool> requestPermissions() async {
    try {
      final androidImplementation =
          _notificationsPlugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
      if (androidImplementation != null) {
        final granted = await androidImplementation.requestNotificationsPermission();
        return granted ?? false;
      }
    } catch (e) {
      if (kDebugMode) {
        print('Notification permission request warning: $e');
      }
    }
    return false;
  }

  Future<void> evaluateAndNotify({
    required String patientId,
    required double riskProbability,
    required String alertSeverity,
    required String recommendedReviewLevel,
  }) async {
    final normalizedSeverity = alertSeverity.toUpperCase();
    final isUrgent = normalizedSeverity.contains('RED') ||
        normalizedSeverity.contains('URGENT') ||
        recommendedReviewLevel.toUpperCase().contains('URGENT');

    final lastSeverity = _lastNotifiedSeverity[patientId];

    if (!isUrgent) {
      // Reset notification state when patient severity drops below URGENT
      _lastNotifiedSeverity.remove(patientId);
      return;
    }

    // Deduplication: Only notify if patient escalated to URGENT or wasn't previously notified as URGENT
    if (lastSeverity == 'URGENT') {
      return;
    }

    _lastNotifiedSeverity[patientId] = 'URGENT';
    await _showUrgentNotification(
      patientId: patientId,
      riskProbability: riskProbability,
      reviewLevel: recommendedReviewLevel,
    );
  }

  Future<void> _showUrgentNotification({
    required String patientId,
    required double riskProbability,
    required String reviewLevel,
  }) async {
    final riskPct = formatRiskPercentage(riskProbability);
    final vibrationPattern = Int64List.fromList([0, 500, 200, 500, 200, 500]);

    final androidDetails = AndroidNotificationDetails(
      channelId,
      channelName,
      channelDescription: channelDescription,
      importance: Importance.max,
      priority: Priority.high,
      playSound: true,
      enableVibration: true,
      vibrationPattern: vibrationPattern,
      styleInformation: BigTextStyleInformation(
        'Patient $patientId — Sepsis Risk: $riskPct\nClinical Action: $reviewLevel',
        contentTitle: 'ARGUS — URGENT CLINICAL ALERT',
        summaryText: 'Critical Risk Escalation',
      ),
    );

    final notificationDetails = NotificationDetails(android: androidDetails);
    final notificationId = patientId.hashCode & 0x7FFFFFFF;

    try {
      await _notificationsPlugin.show(
        notificationId,
        'ARGUS — URGENT CLINICAL ALERT',
        'Patient $patientId — Sepsis Risk: $riskPct% ($reviewLevel)',
        notificationDetails,
        payload: patientId,
      );
    } catch (e) {
      if (kDebugMode) {
        print('Error posting urgent notification: $e');
      }
    }
  }

  void clearPatientNotification(String patientId) {
    _lastNotifiedSeverity.remove(patientId);
  }

  void clearHistory() {
    _lastNotifiedSeverity.clear();
  }
}
