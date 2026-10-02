import 'package:flutter/material.dart';
import '../../core/constants/app_theme.dart';
import '../../core/utils/risk_formatter.dart';
import '../../data/models/prediction_response.dart';

class AlertCard extends StatelessWidget {
  final PredictionResponse alert;
  final VoidCallback onTap;

  const AlertCard({
    super.key,
    required this.alert,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final severity = (alert.alertSeverity ?? 'NONE').toUpperCase();

    Color alertColor;
    IconData alertIcon;

    if (severity == 'RED' || alert.recommendedClinicalReviewLevel == 'URGENT') {
      alertColor = AppColors.redUrgent;
      alertIcon = Icons.warning_rounded;
    } else if (severity == 'ORANGE' || alert.recommendedClinicalReviewLevel == 'REVIEW') {
      alertColor = AppColors.orangeReview;
      alertIcon = Icons.error_outline_rounded;
    } else {
      alertColor = AppColors.yellowWatch;
      alertIcon = Icons.info_outline_rounded;
    }

    final riskPct = 'Risk: ${formatRiskPercentage(alert.riskProbability)}';
    final factorSummary = alert.contributingFactors.isNotEmpty
        ? alert.contributingFactors.first
        : 'Model risk threshold triggered.';

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: alertColor, width: severity == 'RED' ? 2 : 1),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(alertIcon, color: alertColor, size: 22),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Patient: ${alert.patientId}',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(Icons.chevron_right, color: alertColor.withValues(alpha: 0.7), size: 20),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Flexible(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: alertColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: alertColor),
                      ),
                      child: Text(
                        '${alert.recommendedClinicalReviewLevel.toUpperCase()} ($riskPct)',
                        style: TextStyle(
                          color: alertColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                factorSummary,
                style: const TextStyle(fontSize: 12, color: Colors.white70),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
