import 'prediction_response.dart';

class EventEnvelope {
  final String type;
  final DateTime occurredAt;
  final String? patientId;
  final Map<String, dynamic> payload;

  EventEnvelope({
    required this.type,
    required this.occurredAt,
    this.patientId,
    required this.payload,
  });

  factory EventEnvelope.fromJson(Map<String, dynamic> json) {
    DateTime parsedTime;
    if (json['occurred_at'] != null) {
      parsedTime = DateTime.tryParse(json['occurred_at'].toString()) ?? DateTime.now();
    } else {
      parsedTime = DateTime.now();
    }

    final payloadMap = (json['payload'] is Map<String, dynamic>)
        ? (json['payload'] as Map<String, dynamic>)
        : <String, dynamic>{};

    return EventEnvelope(
      type: json['type']?.toString() ?? 'unknown',
      occurredAt: parsedTime,
      patientId: json['patient_id']?.toString(),
      payload: payloadMap,
    );
  }

  bool get isPrediction => type == 'prediction' || payload.containsKey('risk_probability');

  PredictionResponse? toPredictionResponse() {
    if (isPrediction) {
      try {
        final payloadPatientId = payload['patient_id']?.toString();
        if (patientId != null &&
            payloadPatientId != null &&
            payloadPatientId != patientId) {
          return null;
        }
        return PredictionResponse.fromJson(
          payload,
          envelopePatientId: patientId,
        );
      } catch (_) {
        return null;
      }
    }
    return null;
  }
}
