import 'package:flutter/material.dart';
import '../../core/constants/app_theme.dart';
import '../state/app_state.dart';
import '../widgets/connection_status_banner.dart';
import '../widgets/patient_card.dart';

class IcuOverviewScreen extends StatelessWidget {
  final AppState state;
  final Function(String patientId) onSelectPatient;

  const IcuOverviewScreen({
    super.key,
    required this.state,
    required this.onSelectPatient,
  });

  @override
  Widget build(BuildContext context) {
    final staff = state.currentStaff;
    final all = state.myPatients;
    final urgentCount = state.urgentPatients.length;
    final reviewCount = state.reviewPatients.length;
    final watchCount = state.watchPatients.length;

    return Column(
      children: [
        ConnectionStatusBanner(
          status: state.connectionStatus,
          isStaleData: state.isStaleData,
        ),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          color: Colors.blueAccent.withValues(alpha: 0.15),
          child: Row(
            children: [
              const Icon(Icons.badge, size: 18, color: Colors.blueAccent),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Clinician: ${staff.name} (${staff.role} | ${staff.unit})',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: Colors.blueAccent,
                  ),
                ),
              ),
              Text(
                '${all.length} Assigned',
                style: const TextStyle(fontSize: 12, color: Colors.white70),
              ),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          color: AppColors.surfaceDark,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildSummaryPill('Assigned', '${all.length}', Colors.blueAccent),
              _buildSummaryPill('Urgent', '$urgentCount', AppColors.redUrgent),
              _buildSummaryPill('Review', '$reviewCount', AppColors.orangeReview),
              _buildSummaryPill('Watch', '$watchCount', AppColors.yellowWatch),
            ],
          ),
        ),
        Expanded(
          child: all.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.monitor_heart_outlined, size: 48, color: Colors.white24),
                      const SizedBox(height: 12),
                      const Text(
                        'No live patient data available.',
                        style: TextStyle(fontSize: 16, color: Colors.white54),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Connect simulator or backend server stream.',
                        style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.3)),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  itemCount: all.length,
                  itemBuilder: (context, index) {
                    final patient = all[index];
                    return PatientCard(
                      patient: patient,
                      onTap: () => onSelectPatient(patient.patientId),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildSummaryPill(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            style: const TextStyle(fontSize: 10, color: Colors.white70),
          ),
        ],
      ),
    );
  }
}
