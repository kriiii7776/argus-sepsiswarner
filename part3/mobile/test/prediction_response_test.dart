import 'package:flutter_test/flutter_test.dart';
import 'package:argus_mobile/data/models/prediction_response.dart';

void main() {
  group('PredictionResponse Parsing Tests', () {
    test('Parse valid RED URGENT prediction payload from backend', () {
      final json = {
        "patient_id": "PATIENT-001",
        "prediction_timestamp": "2026-10-02T01:15:00Z",
        "prediction_horizon_hours": 6,
        "risk_probability": 0.785,
        "uncertainty_interval": null,
        "uncertainty_summary": {
          "uncertainty_available": false,
          "method": "UNAVAILABLE",
          "reason": "Conformal prediction calibration artifact unavailable in repository",
        },
        "confidence": "HIGH",
        "signal_quality": "HIGH",
        "alert_severity": "RED",
        "recommended_clinical_review_level": "URGENT",
        "contributing_factors": [
          "Heart Rate (115 bpm) elevated above baseline (+25.0 bpm/hr)",
          "MAP (58 mmHg) depressed below baseline (-12.0 mmHg/hr)"
        ],
        "shap_explanation": {
          "explanation_available": true,
          "output_space": "log-odds",
          "base_value_log_odds": -1.842,
          "explained_output_log_odds": 1.295,
          "feature_attributions": [
            {
              "feature": "hr_curr",
              "value": 115.0,
              "attribution_log_odds": 0.854,
              "direction": "increases_risk",
              "description": "hr_curr = 115.00 (+0.854 log-odds)"
            }
          ],
          "top_contributions": [
            {
              "feature": "hr_curr",
              "value": 115.0,
              "attribution_log_odds": 0.854,
              "direction": "increases_risk",
              "description": "hr_curr = 115.00 (+0.854 log-odds)"
            }
          ],
          "model_version": "logistic-regression-v1"
        },
        "alert": {
          "alert_severity": "RED",
          "recommended_clinical_review_level": "URGENT",
          "alert_emitted": true,
        },
        "latency_ms": 14.2,
        "model_version": "logistic-regression-v1",
        "is_demo_model": false
      };

      final response = PredictionResponse.fromJson(json);

      expect(response.patientId, equals("PATIENT-001"));
      expect(response.riskProbability, equals(0.785));
      expect(response.alertSeverity, equals("RED"));
      expect(response.recommendedClinicalReviewLevel, equals("URGENT"));
      expect(response.confidence, equals("HIGH"));
      expect(response.signalQuality, equals("HIGH"));
      expect(response.contributingFactors.length, equals(2));
      expect(response.shapExplanation, isNotNull);
      expect(response.shapExplanation!.explanationAvailable, isTrue);
      expect(response.shapExplanation!.featureAttributions.first.attributionLogOdds, equals(0.854));
      expect(response.isDemoModel, isFalse);
    });

    test('Parse ORANGE REVIEW prediction payload', () {
      final json = {
        "patient_id": "PATIENT-002",
        "prediction_timestamp": "2026-10-02T01:15:00Z",
        "risk_probability": 0.48,
        "confidence": "MEDIUM",
        "signal_quality": "HIGH",
        "alert_severity": "ORANGE",
        "recommended_clinical_review_level": "REVIEW",
        "contributing_factors": ["MAP baseline drop"],
        "latency_ms": 10.0,
        "model_version": "logistic-regression-v1",
        "is_demo_model": false
      };

      final response = PredictionResponse.fromJson(json);

      expect(response.patientId, equals("PATIENT-002"));
      expect(response.riskProbability, equals(0.48));
      expect(response.alertSeverity, equals("ORANGE"));
      expect(response.recommendedClinicalReviewLevel, equals("REVIEW"));
    });

    test('Parse YELLOW WATCH prediction payload', () {
      final json = {
        "patient_id": "PATIENT-003",
        "prediction_timestamp": "2026-10-02T01:15:00Z",
        "risk_probability": 0.28,
        "confidence": "HIGH",
        "signal_quality": "HIGH",
        "alert_severity": "YELLOW",
        "recommended_clinical_review_level": "WATCH",
        "contributing_factors": [],
        "latency_ms": 8.0,
        "model_version": "logistic-regression-v1",
        "is_demo_model": false
      };

      final response = PredictionResponse.fromJson(json);

      expect(response.patientId, equals("PATIENT-003"));
      expect(response.alertSeverity, equals("YELLOW"));
      expect(response.recommendedClinicalReviewLevel, equals("WATCH"));
    });

    test('Parse payload with missing nullable fields safely without throwing', () {
      final json = {
        "patient_id": "PATIENT-NULL",
        "risk_probability": 0.15,
      };

      final response = PredictionResponse.fromJson(json);

      expect(response.patientId, equals("PATIENT-NULL"));
      expect(response.riskProbability, equals(0.15));
      expect(response.alertSeverity, isNull);
      expect(response.shapExplanation, isNull);
      expect(response.uncertaintyInterval, isNull);
      expect(response.confidence, equals("MEDIUM"));
      expect(response.recommendedClinicalReviewLevel, equals("No alert"));
    });

    test('Missing, null, non-finite, or out-of-range risk is unavailable', () {
      final base = <String, dynamic>{'patient_id': 'PATIENT-INVALID'};
      for (final value in <Object?>[null, double.nan, double.infinity, -0.01, 1.01, '0.5']) {
        final response = PredictionResponse.fromJson({...base, 'risk_probability': value});
        expect(response.riskProbability, isNull, reason: 'value=$value');
      }
      expect(PredictionResponse.fromJson(base).riskProbability, isNull);
    });

    test('Risk probability is retained as a fraction for display conversion', () {
      final response = PredictionResponse.fromJson({
        'patient_id': 'PATIENT-PCT',
        'risk_probability': 0.862403,
      });
      expect(response.riskProbability, closeTo(0.862403, 1e-12));
      expect((response.riskProbability! * 100).toStringAsFixed(2), '86.24');
    });
  });
}
