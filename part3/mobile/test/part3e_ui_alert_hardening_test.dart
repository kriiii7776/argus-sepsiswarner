import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:argus_mobile/core/network/websocket_client.dart';
import 'package:argus_mobile/presentation/state/app_state.dart';
import 'package:argus_mobile/presentation/screens/alert_center_screen.dart';
import 'package:argus_mobile/presentation/widgets/shap_contributors_view.dart';
import 'package:argus_mobile/data/models/shap_explanation.dart';

void main() {
  group('Part 3E — Alert Center & UI Hardening Tests', () {
    late AppState appState;
    late WebSocketClient wsClient;

    setUp(() {
      wsClient = WebSocketClient();
      appState = AppState(wsClient: wsClient);
    });

    tearDown(() {
      wsClient.dispose();
      appState.dispose();
    });

    test('Alert state deduplication keeps single active alert card per patient', () {
      final msg1 = {
        "type": "prediction",
        "occurred_at": "2026-10-02T05:00:00Z",
        "patient_id": "PATIENT-001",
        "payload": {
          "patient_id": "PATIENT-001",
          "prediction_timestamp": "2026-10-02T05:00:00Z",
          "risk_probability": 0.45,
          "confidence": "HIGH",
          "signal_quality": "VALID",
          "alert_severity": "YELLOW",
          "recommended_clinical_review_level": "WATCH — CLINICAL MONITORING",
          "contributing_factors": ["hr_slope_4h"],
          "model_version": "logistic-regression-v1",
          "is_demo_model": false,
          "latency_ms": 12.0,
        }
      };

      // Ingest prediction 1
      appState.handleRawMessage(msg1);
      expect(appState.activeAlerts.length, equals(1));
      expect(appState.activeAlerts.first.recommendedClinicalReviewLevel, contains("WATCH"));

      // Ingest prediction 2 for same patient with updated severity (REVIEW)
      final msg2 = Map<String, dynamic>.from(msg1);
      msg2["payload"] = Map<String, dynamic>.from(msg1["payload"] as Map);
      msg2["payload"]["risk_probability"] = 0.65;
      msg2["payload"]["alert_severity"] = "ORANGE";
      msg2["payload"]["recommended_clinical_review_level"] = "REVIEW — PROMPT CLINICAL REVIEW";

      appState.handleRawMessage(msg2);

      // Must remain exactly ONE card for PATIENT-001 with updated severity
      expect(appState.activeAlerts.length, equals(1));
      expect(appState.activeAlerts.first.recommendedClinicalReviewLevel, contains("REVIEW"));
      expect(appState.activeAlerts.first.riskProbability, equals(0.65));

      // Escalation to URGENT
      final msg3 = Map<String, dynamic>.from(msg1);
      msg3["payload"] = Map<String, dynamic>.from(msg1["payload"] as Map);
      msg3["payload"]["risk_probability"] = 0.88;
      msg3["payload"]["alert_severity"] = "RED";
      msg3["payload"]["recommended_clinical_review_level"] = "URGENT — URGENT CLINICAL REVIEW";

      appState.handleRawMessage(msg3);

      expect(appState.activeAlerts.length, equals(1));
      expect(appState.activeAlerts.first.recommendedClinicalReviewLevel, contains("URGENT"));
      expect(appState.activeAlerts.first.riskProbability, equals(0.88));
    });

    test('Separate vital_update messages populate latest vitals map and patient summary', () {
      final vitalMsg = {
        "type": "vital_update",
        "occurred_at": "2026-10-02T05:00:00Z",
        "patient_id": "PATIENT-001",
        "payload": {
          "patient_id": "PATIENT-001",
          "timestamp": "2026-10-02T05:00:00Z",
          "heart_rate": 105.0,
          "map": 78.5,
          "respiratory_rate": 22.0,
          "spo2": 96.0,
          "temperature_c": 38.2,
          "lactate": null
        }
      };

      appState.handleRawMessage(vitalMsg);

      final predMsg = {
        "type": "prediction",
        "occurred_at": "2026-10-02T05:00:01Z",
        "patient_id": "PATIENT-001",
        "payload": {
          "patient_id": "PATIENT-001",
          "prediction_timestamp": "2026-10-02T05:00:01Z",
          "risk_probability": 0.86,
          "confidence": "HIGH",
          "signal_quality": "VALID",
          "alert_severity": "RED",
          "recommended_clinical_review_level": "URGENT — URGENT CLINICAL REVIEW",
          "contributing_factors": ["temp_curr"],
          "model_version": "logistic-regression-v1",
          "is_demo_model": false,
          "latency_ms": 15.0,
        }
      };

      appState.handleRawMessage(predMsg);

      final patient = appState.allPatients.firstWhere((p) => p.patientId == "PATIENT-001");
      expect(patient.latestVitals, isNotNull);
      expect(patient.latestVitals!.heartRate, equals(105.0));
      expect(patient.latestVitals!.map, equals(78.5));
      expect(patient.latestVitals!.lactate, isNull);
    });

    testWidgets('AlertCard renders long review labels on narrow screen without horizontal overflow',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1.0;

      final msg = {
        "type": "prediction",
        "occurred_at": "2026-10-02T05:00:00Z",
        "patient_id": "PATIENT-001",
        "payload": {
          "patient_id": "PATIENT-001",
          "prediction_timestamp": "2026-10-02T05:00:00Z",
          "risk_probability": 0.862,
          "confidence": "HIGH",
          "signal_quality": "VALID",
          "alert_severity": "RED",
          "recommended_clinical_review_level": "URGENT — URGENT CLINICAL REVIEW",
          "contributing_factors": ["hr_slope_4h (+18.5)"],
          "model_version": "logistic-regression-v1",
          "is_demo_model": false,
          "latency_ms": 12.0,
        }
      };

      appState.handleRawMessage(msg);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: AlertCenterScreen(
              state: appState,
              onSelectPatient: (_) {},
            ),
          ),
        ),
      );

      await tester.pump();
      expect(tester.takeException(), isNull);
      expect(find.textContaining('PATIENT-001'), findsOneWidget);

      addTearDown(tester.view.resetPhysicalSize);
    });

    testWidgets('ShapContributorsView displays positive and negative attributions cleanly',
        (WidgetTester tester) async {
      final explanation = ShapExplanation(
        explanationAvailable: true,
        reason: null,
        topContributions: [
          ShapContribution(
            feature: 'temp_curr',
            description: 'temp_curr',
            attributionLogOdds: -0.198,
            value: 36.4,
            direction: 'negative',
          ),
          ShapContribution(
            feature: 'hr_slope_4h',
            description: 'hr_slope_4h',
            attributionLogOdds: 0.187,
            value: 21.9,
            direction: 'positive',
          ),
        ],
        featureAttributions: [],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ShapContributorsView(explanation: explanation),
          ),
        ),
      );

      await tester.pump();
      expect(tester.takeException(), isNull);
      expect(find.text('-0.198'), findsOneWidget);
      expect(find.text('+0.187'), findsOneWidget);
    });
  });
}
