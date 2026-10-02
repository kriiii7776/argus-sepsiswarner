import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:argus_mobile/data/models/event_envelope.dart';
import 'package:argus_mobile/data/models/patient_summary.dart';
import 'package:argus_mobile/data/models/shap_explanation.dart';
import 'package:argus_mobile/data/models/vital_event.dart';
import 'package:argus_mobile/presentation/state/app_state.dart';
import 'package:argus_mobile/presentation/screens/immediate_review_screen.dart';
import 'package:argus_mobile/core/network/websocket_client.dart';

void main() {
  group('A. Prediction Event Parsing Tests', () {
    test('Parse complete prediction payload from backend contract', () {
      final json = {
        "type": "prediction",
        "occurred_at": "2026-10-02T04:00:00Z",
        "patient_id": "PATIENT-001",
        "payload": {
          "patient_id": "PATIENT-001",
          "prediction_timestamp": "2026-10-02T04:00:00Z",
          "risk_probability": 0.862,
          "confidence": "HIGH",
          "signal_quality": "HIGH",
          "alert_severity": "RED — URGENT",
          "recommended_clinical_review_level": "URGENT — urgent clinical review",
          "model_version": "logistic-regression-v1",
          "is_demo_model": false,
          "latency_ms": 12.5,
          "contributing_factors": ["hr_curr elevated"]
        }
      };

      final envelope = EventEnvelope.fromJson(json);
      expect(envelope.isPrediction, isTrue);

      final pred = envelope.toPredictionResponse();
      expect(pred, isNotNull);
      expect(pred!.patientId, equals("PATIENT-001"));
      expect(pred.riskProbability, equals(0.862));
      expect(pred.alertSeverity, equals("RED — URGENT"));
      expect(pred.recommendedClinicalReviewLevel, equals("URGENT — urgent clinical review"));
      expect(pred.modelVersion, equals("logistic-regression-v1"));
    });
  });

  group('B. SHAP Parsing Tests', () {
    test('Parse real backend SHAP attributions with feature_name, shap_value, feature_value', () {
      final json = {
        "explanation_available": true,
        "output_space": "log-odds",
        "base_value_log_odds": -2.145,
        "explained_output_log_odds": 1.832,
        "feature_attributions": [
          {
            "feature_name": "hr_curr",
            "feature_value": 115.0,
            "shap_value": 0.845,
            "contribution_direction": "positive",
            "absolute_contribution": 0.845
          },
          {
            "feature_name": "map_curr",
            "feature_value": 58.0,
            "shap_value": -0.620,
            "contribution_direction": "negative",
            "absolute_contribution": 0.620
          }
        ],
        "top_contributions": [
          {
            "feature_name": "hr_curr",
            "feature_value": 115.0,
            "shap_value": 0.845,
            "contribution_direction": "positive"
          }
        ],
        "model_version": "logistic-regression-v1"
      };

      final shap = ShapExplanation.fromJson(json);
      expect(shap.explanationAvailable, isTrue);
      expect(shap.featureAttributions.length, equals(2));

      final first = shap.featureAttributions.first;
      expect(first.feature, equals("hr_curr"));
      expect(first.value, equals(115.0));
      expect(first.attributionLogOdds, equals(0.845));
      expect(first.direction, equals("positive"));

      final second = shap.featureAttributions.last;
      expect(second.feature, equals("map_curr"));
      expect(second.value, equals(58.0));
      expect(second.attributionLogOdds, equals(-0.620));
    });

    test('Gracefully handle empty or unavailable SHAP explanation', () {
      final json = {
        "explanation_available": false,
        "reason": "SHAP model explanation unavailable"
      };

      final shap = ShapExplanation.fromJson(json);
      expect(shap.explanationAvailable, isFalse);
      expect(shap.featureAttributions, isEmpty);
      expect(shap.reason, equals("SHAP model explanation unavailable"));
    });
  });

  group('C. Alert Counter Aggregation & Escalation Tests', () {
    test('AlertSeverityRank parses RED — URGENT and URGENT — urgent clinical review', () {
      final rankRed = AlertSeverityRank.fromString("RED — URGENT", "URGENT — urgent clinical review");
      expect(rankRed, equals(AlertSeverityRank.redUrgent));

      final rankOrange = AlertSeverityRank.fromString("ORANGE — REVIEW", "REVIEW — prompt clinical review");
      expect(rankOrange, equals(AlertSeverityRank.orangeReview));

      final rankYellow = AlertSeverityRank.fromString("YELLOW — WATCH", "WATCH — routine clinical review");
      expect(rankYellow, equals(AlertSeverityRank.yellowWatch));
    });

    test('AppState maintains single patient state on repeated events and escalation', () {
      // Raw message 1: Watch
      final msg1 = {
        "type": "prediction",
        "patient_id": "PATIENT-001",
        "payload": {
          "patient_id": "PATIENT-001",
          "prediction_timestamp": DateTime.now().toIso8601String(),
          "risk_probability": 0.30,
          "confidence": "HIGH",
          "signal_quality": "HIGH",
          "alert_severity": "YELLOW — WATCH",
          "recommended_clinical_review_level": "WATCH — routine clinical review",
          "model_version": "v1",
          "is_demo_model": false,
          "latency_ms": 5.0,
          "contributing_factors": []
        }
      };

      // Raw message 2: Escalated Urgent
      final msg2 = {
        "type": "prediction",
        "patient_id": "PATIENT-001",
        "payload": {
          "patient_id": "PATIENT-001",
          "prediction_timestamp": DateTime.now().add(const Duration(minutes: 1)).toIso8601String(),
          "risk_probability": 0.862,
          "confidence": "HIGH",
          "signal_quality": "HIGH",
          "alert_severity": "RED — URGENT",
          "recommended_clinical_review_level": "URGENT — urgent clinical review",
          "model_version": "v1",
          "is_demo_model": false,
          "latency_ms": 5.0,
          "contributing_factors": []
        }
      };

      final envelope1 = EventEnvelope.fromJson(msg1);
      final pred1 = envelope1.toPredictionResponse()!;
      final p1 = PatientSummary(
        patientId: "PATIENT-001",
        latestPrediction: pred1,
        lastUpdated: DateTime.now(),
      );
      expect(p1.priorityRank, equals(AlertSeverityRank.yellowWatch));

      final envelope2 = EventEnvelope.fromJson(msg2);
      final pred2 = envelope2.toPredictionResponse()!;
      final p2 = PatientSummary(
        patientId: "PATIENT-001",
        latestPrediction: pred2,
        lastUpdated: DateTime.now(),
      );
      expect(p2.priorityRank, equals(AlertSeverityRank.redUrgent));
    });
  });

  group('D. Vital Mapping & Safety Tests', () {
    test('Map VitalEvent from json with respiratory_rate, temperature_c, map, lactate', () {
      final json = {
        "patient_id": "PATIENT-001",
        "timestamp": "2026-10-02T04:00:00Z",
        "heart_rate": 115.0,
        "map": 70.0,
        "respiratory_rate": 24.0,
        "spo2": 95.0,
        "temperature": 38.5,
        "lactate": 2.4
      };

      final vitals = VitalEvent.fromJson(json);
      expect(vitals.heartRate, equals(115.0));
      expect(vitals.map, equals(70.0));
      expect(vitals.respRate, equals(24.0));
      expect(vitals.spo2, equals(95.0));
      expect(vitals.temperatureC, equals(38.5));
      expect(vitals.lactate, equals(2.4));
    });

    test('Nullable lactate remains null when absent from payload', () {
      final json = {
        "patient_id": "PATIENT-002",
        "timestamp": "2026-10-02T04:00:00Z",
        "heart_rate": 80.0,
        "map": 85.0
      };

      final vitals = VitalEvent.fromJson(json);
      expect(vitals.lactate, isNull);
    });
  });

  group('E. Responsive Layout Widget Tests', () {
    testWidgets('Missing requested patient never displays another patient',
        (WidgetTester tester) async {
      final appState = AppState(wsClient: WebSocketClient());
      appState.handleRawMessage({
        'type': 'prediction',
        'patient_id': 'PATIENT-B',
        'payload': {
          'patient_id': 'PATIENT-B',
          'prediction_timestamp': DateTime.now().toIso8601String(),
          'risk_probability': 0.91,
          'confidence': 'HIGH',
          'signal_quality': 'HIGH',
          'alert_severity': 'RED',
          'recommended_clinical_review_level': 'URGENT',
          'contributing_factors': [],
          'latency_ms': 1.0,
          'model_version': 'test',
          'is_demo_model': false,
        },
      });

      await tester.pumpWidget(MaterialApp(
        home: ImmediateReviewScreen(
          state: appState,
          patientId: 'PATIENT-A',
          onBack: () {},
        ),
      ));
      expect(find.text('Patient data unavailable'), findsOneWidget);
      expect(find.textContaining('91.0%'), findsNothing);
      appState.wsClient.dispose();
      appState.dispose();
    });

    testWidgets('ImmediateReviewScreen renders cleanly on narrow screen without horizontal overflow',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      final appState = AppState(wsClient: WebSocketClient());

      final msg = {
        "type": "prediction",
        "patient_id": "P-MIMIC-LONG-IDENTIFIER-999",
        "payload": {
          "patient_id": "P-MIMIC-LONG-IDENTIFIER-999",
          "prediction_timestamp": DateTime.now().toIso8601String(),
          "risk_probability": 0.862,
          "confidence": "HIGH",
          "signal_quality": "HIGH",
          "alert_severity": "RED — URGENT",
          "recommended_clinical_review_level": "URGENT — urgent clinical review",
          "model_version": "logistic-regression-v1-production-extended-long-name",
          "is_demo_model": false,
          "latency_ms": 12.0,
          "contributing_factors": []
        }
      };

      appState.handleRawMessage(msg);
      appState.selectPatient("P-MIMIC-LONG-IDENTIFIER-999");

      // Create a MaterialApp containing ImmediateReviewScreen
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ImmediateReviewScreen(
              state: appState,
              patientId: "P-MIMIC-LONG-IDENTIFIER-999",
              onBack: () {},
            ),
          ),
        ),
      );

      await tester.pump();

      expect(tester.takeException(), isNull);
      appState.wsClient.dispose();
      appState.dispose();
    });
  });
}
