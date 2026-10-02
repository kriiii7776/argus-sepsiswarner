class VitalEvent {
  final String patientId;
  final DateTime timestamp;
  final double? heartRate;
  final double? map;
  final double? respRate;
  final double? spo2;
  final double? temperatureC;
  final double? lactate;
  final String source;

  VitalEvent({
    required this.patientId,
    required this.timestamp,
    this.heartRate,
    this.map,
    this.respRate,
    this.spo2,
    this.temperatureC,
    this.lactate,
    this.source = 'simulator',
  });

  factory VitalEvent.fromJson(Map<String, dynamic> json) {
    DateTime parsedTime;
    if (json['timestamp'] != null) {
      parsedTime = DateTime.tryParse(json['timestamp'].toString()) ?? DateTime.now();
    } else if (json['prediction_timestamp'] != null) {
      parsedTime = DateTime.tryParse(json['prediction_timestamp'].toString()) ?? DateTime.now();
    } else {
      parsedTime = DateTime.now();
    }

    final vMap = (json['vitals'] is Map<String, dynamic>)
        ? (json['vitals'] as Map<String, dynamic>)
        : json;

    return VitalEvent(
      patientId: json['patient_id']?.toString() ?? vMap['patient_id']?.toString() ?? 'unknown',
      timestamp: parsedTime,
      heartRate: (vMap['heart_rate'] as num?)?.toDouble() ?? (vMap['heartRate'] as num?)?.toDouble(),
      map: (vMap['map'] as num?)?.toDouble() ?? (vMap['mean_arterial_pressure'] as num?)?.toDouble(),
      respRate: (vMap['resp_rate'] as num?)?.toDouble() ?? (vMap['respiratory_rate'] as num?)?.toDouble() ?? (vMap['respRate'] as num?)?.toDouble(),
      spo2: (vMap['spo2'] as num?)?.toDouble(),
      temperatureC: (vMap['temperature_c'] as num?)?.toDouble() ?? (vMap['temperature'] as num?)?.toDouble() ?? (vMap['temperatureC'] as num?)?.toDouble(),
      lactate: (vMap['lactate'] as num?)?.toDouble(),
      source: json['source']?.toString() ?? 'simulator',
    );
  }
}
