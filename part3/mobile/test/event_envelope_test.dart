import 'package:flutter_test/flutter_test.dart';
import 'package:argus_mobile/data/models/event_envelope.dart';
import 'package:argus_mobile/data/models/vital_event.dart';

void main() {
  group('EventEnvelope Parsing Tests', () {
    test('Parse valid prediction envelope', () {
      final json = {
        "type": "prediction",
        "occurred_at": "2026-10-02T01:15:00Z",
        "patient_id": "PATIENT-001",
        "payload": {
          "patient_id": "PATIENT-001",
          "prediction_timestamp": "2026-10-02T01:15:00Z",
          "risk_probability": 0.82,
          "confidence": "HIGH",
          "signal_quality": "HIGH",
          "alert_severity": "RED",
          "recommended_clinical_review_level": "URGENT",
          "contributing_factors": ["High HR"],
          "latency_ms": 12.0,
          "model_version": "logistic-regression-v1",
          "is_demo_model": false
        }
      };

      final envelope = EventEnvelope.fromJson(json);

      expect(envelope.type, equals("prediction"));
      expect(envelope.patientId, equals("PATIENT-001"));
      expect(envelope.isPrediction, isTrue);

      final pred = envelope.toPredictionResponse();
      expect(pred, isNotNull);
      expect(pred!.riskProbability, equals(0.82));
      expect(pred.alertSeverity, equals("RED"));
    });

    test('Parse vital_event envelope', () {
      final json = {
        "type": "vital_event",
        "occurred_at": "2026-10-02T01:15:00Z",
        "patient_id": "PATIENT-001",
        "payload": {
          "patient_id": "PATIENT-001",
          "timestamp": "2026-10-02T01:15:00Z",
          "heart_rate": 118.0,
          "map": 59.0,
          "resp_rate": 24.0,
          "spo2": 94.0,
          "temperature_c": 38.5,
          "lactate": 2.4,
          "source": "simulator"
        }
      };

      final envelope = EventEnvelope.fromJson(json);

      expect(envelope.type, equals("vital_event"));
      expect(envelope.patientId, equals("PATIENT-001"));

      final vitals = VitalEvent.fromJson(envelope.payload);
      expect(vitals.heartRate, equals(118.0));
      expect(vitals.map, equals(59.0));
      expect(vitals.lactate, equals(2.4));
    });

    test('Handle unknown message type or malformed payload without crash', () {
      final json = {
        "type": "unknown_system_event",
        "occurred_at": "2026-10-02T01:15:00Z",
        "payload": {}
      };

      final envelope = EventEnvelope.fromJson(json);

      expect(envelope.type, equals("unknown_system_event"));
      expect(envelope.isPrediction, isFalse);
      expect(envelope.toPredictionResponse(), isNull);
    });

    test('Reject prediction whose payload patient conflicts with envelope', () {
      final envelope = EventEnvelope.fromJson({
        'type': 'prediction',
        'patient_id': 'PATIENT-A',
        'payload': {
          'patient_id': 'PATIENT-B',
          'risk_probability': 0.9,
        },
      });
      expect(envelope.toPredictionResponse(), isNull);
    });
  });
}
