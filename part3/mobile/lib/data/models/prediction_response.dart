import 'shap_explanation.dart';

class PredictionResponse {
  final String patientId;
  final DateTime predictionTimestamp;
  final int predictionHorizonHours;
  final double? riskProbability;
  final List<double>? uncertaintyInterval;
  final Map<String, dynamic>? uncertaintySummary;
  final String confidence;
  final String signalQuality;
  final String? alertSeverity;
  final String recommendedClinicalReviewLevel;
  final List<String> contributingFactors;
  final ShapExplanation? shapExplanation;
  final Map<String, dynamic>? alert;
  final double latencyMs;
  final String modelVersion;
  final bool isDemoModel;

  PredictionResponse({
    required this.patientId,
    required this.predictionTimestamp,
    this.predictionHorizonHours = 6,
    required this.riskProbability,
    this.uncertaintyInterval,
    this.uncertaintySummary,
    required this.confidence,
    required this.signalQuality,
    this.alertSeverity,
    required this.recommendedClinicalReviewLevel,
    required this.contributingFactors,
    this.shapExplanation,
    this.alert,
    required this.latencyMs,
    required this.modelVersion,
    required this.isDemoModel,
  });

  String get alertId {
    if (alert != null && alert!['alert_id'] != null) {
      return alert!['alert_id'].toString();
    }
    return 'alert-$patientId-${predictionTimestamp.millisecondsSinceEpoch ~/ 1000}';
  }

  factory PredictionResponse.fromJson(Map<String, dynamic> json, {String? envelopePatientId}) {
    DateTime parsedTs;
    if (json['prediction_timestamp'] != null) {
      parsedTs = DateTime.tryParse(json['prediction_timestamp'].toString()) ??
          DateTime.now();
    } else {
      parsedTs = DateTime.now();
    }

    List<double>? interval;
    if (json['uncertainty_interval'] is List) {
      interval = (json['uncertainty_interval'] as List)
          .whereType<num>()
          .map((n) => n.toDouble())
          .toList();
    }

    ShapExplanation? shap;
    if (json['shap_explanation'] is Map<String, dynamic>) {
      shap = ShapExplanation.fromJson(
          json['shap_explanation'] as Map<String, dynamic>);
    }

    final factors = (json['contributing_factors'] as List<dynamic>?)
            ?.map((e) => e.toString())
            .toList() ??
        [];

    final rawRisk = json['risk_probability'];
    final parsedRisk = rawRisk is num ? rawRisk.toDouble() : null;
    final risk = parsedRisk != null &&
            parsedRisk.isFinite &&
            parsedRisk >= 0.0 &&
            parsedRisk <= 1.0
        ? parsedRisk
        : null;

    return PredictionResponse(
      patientId: json['patient_id']?.toString() ?? envelopePatientId ?? 'unknown',
      predictionTimestamp: parsedTs,
      predictionHorizonHours: (json['prediction_horizon_hours'] as num?)?.toInt() ?? 6,
      riskProbability: risk,
      uncertaintyInterval: interval,
      uncertaintySummary: json['uncertainty_summary'] as Map<String, dynamic>?,
      confidence: json['confidence']?.toString() ?? 'MEDIUM',
      signalQuality: json['signal_quality']?.toString() ?? 'HIGH',
      alertSeverity: json['alert_severity']?.toString(),
      recommendedClinicalReviewLevel:
          json['recommended_clinical_review_level']?.toString() ?? 'No alert',
      contributingFactors: factors,
      shapExplanation: shap,
      alert: json['alert'] as Map<String, dynamic>?,
      latencyMs: (json['latency_ms'] as num?)?.toDouble() ?? 0.0,
      modelVersion: json['model_version']?.toString() ?? 'unknown',
      isDemoModel: json['is_demo_model'] == true,
    );
  }
}
