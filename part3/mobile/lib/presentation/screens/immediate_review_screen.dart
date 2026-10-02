import 'package:flutter/material.dart';
import '../../core/constants/app_theme.dart';
import '../../core/utils/risk_formatter.dart';
import '../state/app_state.dart';
import '../widgets/connection_status_banner.dart';
import '../widgets/shap_contributors_view.dart';
import '../widgets/vitals_grid_view.dart';

class ImmediateReviewScreen extends StatelessWidget {
  final AppState state;
  final String patientId;
  final VoidCallback onBack;

  const ImmediateReviewScreen({
    super.key,
    required this.state,
    required this.patientId,
    required this.onBack,
  });

  @override
  Widget build(BuildContext context) {
    final matches = state.allPatients.where((p) => p.patientId == patientId);
    if (matches.isEmpty) {
      return Scaffold(
        appBar: AppBar(
          leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: onBack),
          title: Text('Bedside Review: $patientId'),
          backgroundColor: AppColors.surfaceDark,
        ),
        body: const Center(child: Text('Patient data unavailable')),
      );
    }
    final patient = matches.first;

    final pred = patient.latestPrediction;
    final vitals = patient.latestVitals;
    final rank = patient.priorityRank;

    final bannerColor = rank.rank == 1
        ? AppColors.redUrgent
        : rank.rank == 2
            ? AppColors.orangeReview
            : rank.rank == 3
                ? AppColors.yellowWatch
                : Colors.blueGrey;

    final riskPct = formatRiskPercentage(pred.riskProbability);
    final isLowQuality = pred.signalQuality == 'LOW';
    final isStale = state.isStaleData ||
        DateTime.now().difference(patient.lastUpdated) > const Duration(seconds: 30);

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: onBack,
        ),
        title: Text('Bedside Review: $patientId'),
        backgroundColor: AppColors.surfaceDark,
      ),
      body: Column(
        children: [
          ConnectionStatusBanner(
            status: state.connectionStatus,
            isStaleData: state.isStaleData,
          ),
          if (isStale)
            const Padding(
              padding: EdgeInsets.all(8),
              child: Text('STALE PATIENT DATA', style: TextStyle(color: Colors.amber)),
            ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: bannerColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: bannerColor, width: 2),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'RISK PROBABILITY: $riskPct',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: bannerColor,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: bannerColor,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                pred.recommendedClinicalReviewLevel.toUpperCase(),
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 11,
                                ),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          'Model Version: ${pred.modelVersion} (${pred.isDemoModel ? "Demo Fallback" : "Standard Runtime"})',
                          style: const TextStyle(fontSize: 12, color: Colors.white60),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Timestamp: ${pred.predictionTimestamp.toIso8601String()}',
                          style: const TextStyle(fontSize: 12, color: Colors.white60),
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: state.isAlertAcknowledged(patientId)
                                  ? Colors.green.withValues(alpha: 0.3)
                                  : bannerColor,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 10),
                            ),
                            icon: Icon(
                              state.isAlertAcknowledged(patientId)
                                  ? Icons.check_circle
                                  : Icons.assignment_turned_in,
                              size: 18,
                            ),
                            label: Text(
                              state.isAlertAcknowledged(patientId)
                                  ? 'Alert Acknowledged by ${state.currentStaff.name}'
                                  : 'ACKNOWLEDGE ALERT',
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                            ),
                            onPressed: state.isAlertAcknowledged(patientId)
                                ? null
                                : () {
                                    state.acknowledgeAlert(patientId);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text('Alert acknowledged for $patientId'),
                                      ),
                                    );
                                  },
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (isLowQuality)
                    Container(
                      margin: const EdgeInsets.only(bottom: 16),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.amber.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.amber),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.warning_amber_rounded, color: Colors.amber),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Low signal quality — interpret with caution.',
                              style: TextStyle(
                                color: Colors.amber,
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  const Text(
                    'LATEST VITAL SIGNS',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white70),
                  ),
                  const SizedBox(height: 8),
                  VitalsGridView(vitals: vitals),
                  const SizedBox(height: 20),
                  ShapContributorsView(explanation: pred.shapExplanation),
                  const SizedBox(height: 16),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.03),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.white12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.info_outline, size: 14, color: Colors.white54),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                pred.uncertaintySummary != null &&
                                        pred.uncertaintySummary!['uncertainty_available'] == true
                                    ? 'Uncertainty Interval: ${pred.uncertaintyInterval}'
                                    : 'Statistical uncertainty unavailable for current model.',
                                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.white70),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'ARGUS is a clinical decision-support prototype. Requires clinician review.',
                          style: TextStyle(fontSize: 11, color: Colors.white38, fontStyle: FontStyle.italic),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
