import 'package:flutter_test/flutter_test.dart';
import 'package:argus_mobile/data/models/patient_summary.dart';
import 'package:argus_mobile/data/models/prediction_response.dart';

void main() {
  group('Patient Priority Sorting Tests', () {
    test('Sort patients by RED URGENT > ORANGE REVIEW > YELLOW WATCH > NONE', () {
      final now = DateTime.now();

      final pRed = PatientSummary(
        patientId: "PATIENT-RED",
        latestPrediction: PredictionResponse(
          patientId: "PATIENT-RED",
          predictionTimestamp: now,
          riskProbability: 0.85,
          confidence: "HIGH",
          signalQuality: "HIGH",
          alertSeverity: "RED",
          recommendedClinicalReviewLevel: "URGENT",
          contributingFactors: [],
          latencyMs: 10,
          modelVersion: "lr-v1",
          isDemoModel: false,
        ),
        lastUpdated: now,
      );

      final pOrange = PatientSummary(
        patientId: "PATIENT-ORANGE",
        latestPrediction: PredictionResponse(
          patientId: "PATIENT-ORANGE",
          predictionTimestamp: now,
          riskProbability: 0.52,
          confidence: "HIGH",
          signalQuality: "HIGH",
          alertSeverity: "ORANGE",
          recommendedClinicalReviewLevel: "REVIEW",
          contributingFactors: [],
          latencyMs: 10,
          modelVersion: "lr-v1",
          isDemoModel: false,
        ),
        lastUpdated: now,
      );

      final pYellow = PatientSummary(
        patientId: "PATIENT-YELLOW",
        latestPrediction: PredictionResponse(
          patientId: "PATIENT-YELLOW",
          predictionTimestamp: now,
          riskProbability: 0.28,
          confidence: "HIGH",
          signalQuality: "HIGH",
          alertSeverity: "YELLOW",
          recommendedClinicalReviewLevel: "WATCH",
          contributingFactors: [],
          latencyMs: 10,
          modelVersion: "lr-v1",
          isDemoModel: false,
        ),
        lastUpdated: now,
      );

      final pNone = PatientSummary(
        patientId: "PATIENT-NONE",
        latestPrediction: PredictionResponse(
          patientId: "PATIENT-NONE",
          predictionTimestamp: now,
          riskProbability: 0.08,
          confidence: "HIGH",
          signalQuality: "HIGH",
          alertSeverity: null,
          recommendedClinicalReviewLevel: "No alert",
          contributingFactors: [],
          latencyMs: 10,
          modelVersion: "lr-v1",
          isDemoModel: false,
        ),
        lastUpdated: now,
      );

      final unsorted = [pNone, pYellow, pRed, pOrange];

      unsorted.sort((a, b) => a.priorityRank.rank.compareTo(b.priorityRank.rank));

      expect(unsorted[0].patientId, equals("PATIENT-RED"));
      expect(unsorted[1].patientId, equals("PATIENT-ORANGE"));
      expect(unsorted[2].patientId, equals("PATIENT-YELLOW"));
      expect(unsorted[3].patientId, equals("PATIENT-NONE"));
    });
  });
}
