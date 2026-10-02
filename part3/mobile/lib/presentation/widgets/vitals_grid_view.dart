import 'package:flutter/material.dart';
import '../../data/models/vital_event.dart';

class VitalsGridView extends StatelessWidget {
  final VitalEvent? vitals;

  const VitalsGridView({super.key, this.vitals});

  @override
  Widget build(BuildContext context) {
    if (vitals == null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Center(
          child: Text(
            'Latest vitals unavailable',
            style: TextStyle(color: Colors.white54, fontSize: 13),
          ),
        ),
      );
    }

    final items = [
      {'label': 'Heart Rate', 'value': vitals!.heartRate != null ? '${vitals!.heartRate!.toStringAsFixed(0)} bpm' : 'N/A'},
      {'label': 'MAP', 'value': vitals!.map != null ? '${vitals!.map!.toStringAsFixed(1)} mmHg' : 'N/A'},
      {'label': 'Resp Rate', 'value': vitals!.respRate != null ? '${vitals!.respRate!.toStringAsFixed(0)} /min' : 'N/A'},
      {'label': 'SpO2', 'value': vitals!.spo2 != null ? '${vitals!.spo2!.toStringAsFixed(1)} %' : 'N/A'},
      {'label': 'Temperature', 'value': vitals!.temperatureC != null ? '${vitals!.temperatureC!.toStringAsFixed(1)} °C' : 'N/A'},
      {'label': 'Lactate', 'value': vitals!.lactate != null ? '${vitals!.lactate!.toStringAsFixed(2)} mmol/L' : 'Not available'},
    ];

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        childAspectRatio: 1.8,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        final isMissing = item['value'] == 'N/A' || item['value'] == 'Not available' || item['value'] == '--';

        return Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: isMissing ? Colors.white.withValues(alpha: 0.02) : Colors.white.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isMissing ? Colors.white12 : Colors.white24,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                item['label']!,
                style: const TextStyle(fontSize: 11, color: Colors.white54),
              ),
              const SizedBox(height: 2),
              Text(
                item['value']!,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: isMissing ? Colors.white38 : Colors.white,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
