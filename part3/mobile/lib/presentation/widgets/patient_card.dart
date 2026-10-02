import 'package:flutter/material.dart';
import '../../core/constants/app_theme.dart';
import '../../core/utils/risk_formatter.dart';
import '../../data/models/patient_summary.dart';

class PatientCard extends StatelessWidget {
  final PatientSummary patient;
  final VoidCallback onTap;

  const PatientCard({
    super.key,
    required this.patient,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final rank = patient.priorityRank;
    final pred = patient.latestPrediction;

    final borderColor = rank.rank == 1
        ? AppColors.redUrgent
        : rank.rank == 2
            ? AppColors.orangeReview
            : rank.rank == 3
                ? AppColors.yellowWatch
                : Colors.grey.shade700;
    final bgColor = rank.rank == 1
        ? AppColors.redUrgentBg.withValues(alpha: 0.08)
        : rank.rank == 2
            ? AppColors.orangeReviewBg.withValues(alpha: 0.08)
            : rank.rank == 3
                ? AppColors.yellowWatchBg.withValues(alpha: 0.08)
                : AppColors.cardBackground;

    final riskPct = 'Risk: ${formatRiskPercentage(pred.riskProbability)}';
    final timeStr =
        '${pred.predictionTimestamp.hour.toString().padLeft(2, '0')}:${pred.predictionTimestamp.minute.toString().padLeft(2, '0')}';

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      color: bgColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: borderColor, width: rank == AlertSeverityRank.redUrgent ? 2 : 1),
      ),
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        title: Row(
          children: [
            Expanded(
              child: Text(
                patient.patientId,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: borderColor.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: borderColor),
              ),
              child: Text(
                riskPct,
                style: TextStyle(
                  color: borderColor,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
            ),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 8.0),
          child: Row(
            children: [
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.white10,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    pred.recommendedClinicalReviewLevel.toUpperCase(),
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              if (pred.signalQuality == 'LOW')
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: const BoxDecoration(
                    color: Colors.amber,
                    borderRadius: BorderRadius.all(Radius.circular(4)),
                  ),
                  child: const Text(
                    'LOW SIGNAL QUALITY',
                    style: TextStyle(fontSize: 10, color: Colors.black, fontWeight: FontWeight.bold),
                  ),
                ),
              const Spacer(),
              Text(
                timeStr,
                style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 12),
              ),
            ],
          ),
        ),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}
