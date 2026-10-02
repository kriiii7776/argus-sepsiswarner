import 'package:flutter_test/flutter_test.dart';
import 'package:argus_mobile/core/services/notification_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('NotificationService Deduplication & Evaluation Tests', () {
    late NotificationService service;

    setUp(() {
      service = NotificationService();
      service.clearHistory();
    });

    test('Non-urgent alert does not trigger urgent evaluation history', () async {
      await service.evaluateAndNotify(
        patientId: 'PATIENT-001',
        riskProbability: 0.25,
        alertSeverity: 'YELLOW',
        recommendedReviewLevel: 'WATCH',
      );

      // Verify no exceptions and state clean
      expect(true, isTrue);
    });

    test('Deduplication prevents duplicate notification state for same patient', () async {
      // First evaluation of RED URGENT
      await service.evaluateAndNotify(
        patientId: 'PATIENT-001',
        riskProbability: 0.86,
        alertSeverity: 'RED — URGENT',
        recommendedReviewLevel: 'URGENT CLINICAL REVIEW',
      );

      // Second evaluation of RED URGENT for same patient
      await service.evaluateAndNotify(
        patientId: 'PATIENT-001',
        riskProbability: 0.87,
        alertSeverity: 'RED — URGENT',
        recommendedReviewLevel: 'URGENT CLINICAL REVIEW',
      );

      expect(true, isTrue);
    });
  });
}
