import 'dart:async';
import 'package:flutter/foundation.dart';
import '../../core/network/websocket_client.dart';
import '../../data/models/event_envelope.dart';
import '../../data/models/prediction_response.dart';
import '../../data/models/patient_summary.dart';
import '../../data/models/vital_event.dart';
import '../../core/services/notification_service.dart';

class StaffProfile {
  final String userId;
  final String name;
  final String role;
  final String unit;
  final List<String> assignedPatients;

  const StaffProfile({
    required this.userId,
    required this.name,
    required this.role,
    required this.unit,
    required this.assignedPatients,
  });
}

class AppState extends ChangeNotifier {
  final WebSocketClient wsClient;

  static const Map<String, StaffProfile> availableStaff = {
    'USER-001': StaffProfile(
      userId: 'USER-001',
      name: 'Dr. Arun',
      role: 'DOCTOR',
      unit: 'ICU-A',
      assignedPatients: ['PATIENT-001', 'PATIENT-002'],
    ),
    'USER-002': StaffProfile(
      userId: 'USER-002',
      name: 'Nurse Priya',
      role: 'NURSE',
      unit: 'ICU-A',
      assignedPatients: ['PATIENT-001', 'PATIENT-003'],
    ),
    'USER-003': StaffProfile(
      userId: 'USER-003',
      name: 'Dr. Vikram',
      role: 'DOCTOR',
      unit: 'ICU-B',
      assignedPatients: ['PATIENT-003', 'PATIENT-004'],
    ),
    'USER-004': StaffProfile(
      userId: 'USER-004',
      name: 'Nurse Sunita',
      role: 'NURSE',
      unit: 'ICU-B',
      assignedPatients: ['PATIENT-002', 'PATIENT-004'],
    ),
  };

  String _currentUserId = 'USER-001';
  final Map<String, PatientSummary> _patientsMap = {};
  final Map<String, PredictionResponse> _activeAlertsMap = {};
  final Map<String, VitalEvent> _latestVitalsMap = {};
  final Set<String> _acknowledgedAlerts = {};
  String? _selectedPatientId;
  StreamSubscription? _wsSubscription;

  AppState({required this.wsClient}) {
    wsClient.addListener(_onWsStatusChanged);
    _wsSubscription = wsClient.messageStream.listen(_onWsMessageReceived);
    wsClient.connect();
  }

  String get currentUserId => _currentUserId;
  StaffProfile get currentStaff => availableStaff[_currentUserId] ?? availableStaff.values.first;

  void setCurrentUser(String userId) {
    if (availableStaff.containsKey(userId) && _currentUserId != userId) {
      _currentUserId = userId;
      // Reconnect WebSocket with new staff user ID for patient isolation
      wsClient.updateServerUrl('http://localhost:8000', userId: _currentUserId);
      notifyListeners();
    }
  }

  ConnectionStatus get connectionStatus => wsClient.status;
  bool get isStaleData => wsClient.isStaleData;

  List<PatientSummary> get allPatients {
    final list = _patientsMap.values.toList();
    list.sort((a, b) {
      final rankComp = a.priorityRank.rank.compareTo(b.priorityRank.rank);
      if (rankComp != 0) return rankComp;
      return b.latestPrediction.predictionTimestamp
          .compareTo(a.latestPrediction.predictionTimestamp);
    });
    return list;
  }

  List<PatientSummary> get myPatients {
    final assigned = currentStaff.assignedPatients.toSet();
    return allPatients.where((p) => assigned.contains(p.patientId)).toList();
  }

  List<PatientSummary> get urgentPatients =>
      myPatients.where((p) => p.priorityRank == AlertSeverityRank.redUrgent).toList();

  List<PatientSummary> get reviewPatients =>
      myPatients.where((p) => p.priorityRank == AlertSeverityRank.orangeReview).toList();

  List<PatientSummary> get watchPatients =>
      myPatients.where((p) => p.priorityRank == AlertSeverityRank.yellowWatch).toList();

  List<PredictionResponse> get activeAlerts {
    final list = _activeAlertsMap.values.where((a) => !isAlertAcknowledged(a.patientId)).toList();
    list.sort((a, b) {
      final rankA = AlertSeverityRank.fromString(a.alertSeverity, a.recommendedClinicalReviewLevel).rank;
      final rankB = AlertSeverityRank.fromString(b.alertSeverity, b.recommendedClinicalReviewLevel).rank;
      final comp = rankA.compareTo(rankB);
      if (comp != 0) return comp;
      return b.predictionTimestamp.compareTo(a.predictionTimestamp);
    });
    return list;
  }

  List<PredictionResponse> get myAlerts {
    final assigned = currentStaff.assignedPatients.toSet();
    return activeAlerts.where((a) => assigned.contains(a.patientId)).toList();
  }

  bool isAlertAcknowledged(String patientId) {
    return _acknowledgedAlerts.contains(patientId);
  }

  void acknowledgeAlert(String patientId) {
    _acknowledgedAlerts.add(patientId);
    notifyListeners();
  }

  String? get selectedPatientId => _selectedPatientId;

  PatientSummary? get selectedPatient =>
      _selectedPatientId != null ? _patientsMap[_selectedPatientId] : null;

  void selectPatient(String patientId) {
    _selectedPatientId = patientId;
    notifyListeners();
  }

  void _onWsStatusChanged() {
    notifyListeners();
  }

  void handleRawMessage(Map<String, dynamic> rawMessage) => _onWsMessageReceived(rawMessage);

  void _onWsMessageReceived(Map<String, dynamic> rawMessage) {
    try {
      final envelope = EventEnvelope.fromJson(rawMessage);

      if (envelope.isPrediction) {
        final prediction = envelope.toPredictionResponse();
        if (prediction != null) {
          VitalEvent? extractedVitals;
          if (envelope.payload.containsKey('vitals') ||
              envelope.payload.containsKey('heart_rate') ||
              envelope.payload.containsKey('heartRate')) {
            extractedVitals = VitalEvent.fromJson(envelope.payload);
          } else if (rawMessage.containsKey('vitals')) {
            extractedVitals = VitalEvent.fromJson(rawMessage);
          }
          _ingestPrediction(prediction, vitals: extractedVitals);
        }
      } else if (envelope.type == 'vital_event' || envelope.type == 'vital_update') {
        final vitals = VitalEvent.fromJson(envelope.payload);
        _ingestVitals(vitals);
      }
    } catch (e) {
      if (kDebugMode) {
        print('Error parsing WebSocket message in AppState: $e');
      }
    }
  }

  void _ingestPrediction(PredictionResponse prediction, {VitalEvent? vitals}) {
    final pid = prediction.patientId;
    if (vitals != null) {
      _latestVitalsMap[pid] = vitals;
    }
    final resolvedVitals = vitals ?? _latestVitalsMap[pid] ?? _patientsMap[pid]?.latestVitals;

    _patientsMap[pid] = PatientSummary(
      patientId: pid,
      latestPrediction: prediction,
      latestVitals: resolvedVitals,
      lastUpdated: DateTime.now(),
    );

    final rank = AlertSeverityRank.fromString(
      prediction.alertSeverity,
      prediction.recommendedClinicalReviewLevel,
    );

    if (rank != AlertSeverityRank.none) {
      _activeAlertsMap[pid] = prediction;
    } else {
      _activeAlertsMap.remove(pid);
    }

    final risk = prediction.riskProbability;
    if (risk != null) {
      NotificationService.instance.evaluateAndNotify(
        patientId: pid,
        riskProbability: risk,
        alertSeverity: prediction.alertSeverity ?? '',
        recommendedReviewLevel: prediction.recommendedClinicalReviewLevel,
      );
    }

    notifyListeners();
  }

  void _ingestVitals(VitalEvent vitals) {
    final pid = vitals.patientId;
    _latestVitalsMap[pid] = vitals;
    final existing = _patientsMap[pid];

    if (existing != null) {
      _patientsMap[pid] = PatientSummary(
        patientId: pid,
        latestPrediction: existing.latestPrediction,
        latestVitals: vitals,
        lastUpdated: DateTime.now(),
      );
    }
    notifyListeners();
  }

  void updateServerUrl(String url) {
    wsClient.updateServerUrl(url, userId: _currentUserId);
  }

  @override
  void dispose() {
    wsSubscriptionCancel();
    wsClient.removeListener(_onWsStatusChanged);
    super.dispose();
  }

  void wsSubscriptionCancel() {
    _wsSubscription?.cancel();
  }
}
