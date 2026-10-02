import 'prediction_response.dart';
import 'vital_event.dart';

enum AlertSeverityRank {
  redUrgent(1, 'RED', 'URGENT'),
  orangeReview(2, 'ORANGE', 'REVIEW'),
  yellowWatch(3, 'YELLOW', 'WATCH'),
  none(4, 'NONE', 'No alert');

  final int rank;
  final String severityCode;
  final String reviewLevelLabel;

  const AlertSeverityRank(this.rank, this.severityCode, this.reviewLevelLabel);

  static AlertSeverityRank fromString(String? severity, String? reviewLevel) {
    final s = (severity ?? '').toUpperCase();
    final r = (reviewLevel ?? '').toUpperCase();

    if (s.contains('RED') || s.contains('CRITICAL') || r.startsWith('URGENT')) {
      return AlertSeverityRank.redUrgent;
    } else if (s.contains('ORANGE') || r.startsWith('REVIEW') || r.contains('PROMPT')) {
      return AlertSeverityRank.orangeReview;
    } else if (s.contains('YELLOW') || r.startsWith('WATCH') || r.contains('ROUTINE')) {
      return AlertSeverityRank.yellowWatch;
    }
    return AlertSeverityRank.none;
  }
}

class PatientSummary {
  final String patientId;
  final PredictionResponse latestPrediction;
  final VitalEvent? latestVitals;
  final DateTime lastUpdated;

  PatientSummary({
    required this.patientId,
    required this.latestPrediction,
    this.latestVitals,
    required this.lastUpdated,
  });

  AlertSeverityRank get priorityRank => AlertSeverityRank.fromString(
        latestPrediction.alertSeverity,
        latestPrediction.recommendedClinicalReviewLevel,
      );

  double? get riskPercentage =>
      latestPrediction.riskProbability == null
          ? null
          : latestPrediction.riskProbability! * 100.0;
}
