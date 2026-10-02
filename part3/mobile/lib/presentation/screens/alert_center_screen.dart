import 'package:flutter/material.dart';
import '../state/app_state.dart';
import '../widgets/alert_card.dart';
import '../widgets/connection_status_banner.dart';

class AlertCenterScreen extends StatelessWidget {
  final AppState state;
  final Function(String patientId) onSelectPatient;

  const AlertCenterScreen({
    super.key,
    required this.state,
    required this.onSelectPatient,
  });

  @override
  Widget build(BuildContext context) {
    final alerts = state.myAlerts;

    return Column(
      children: [
        ConnectionStatusBanner(
          status: state.connectionStatus,
          isStaleData: state.isStaleData,
        ),
        Expanded(
          child: alerts.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.notifications_off_outlined, size: 48, color: Colors.white24),
                      const SizedBox(height: 12),
                      const Text(
                        'No active clinical alerts.',
                        style: TextStyle(fontSize: 16, color: Colors.white54),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'All monitored patients below alert thresholds.',
                        style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.3)),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  itemCount: alerts.length,
                  itemBuilder: (context, index) {
                    final alert = alerts[index];
                    return AlertCard(
                      alert: alert,
                      onTap: () => onSelectPatient(alert.patientId),
                    );
                  },
                ),
        ),
      ],
    );
  }
}
