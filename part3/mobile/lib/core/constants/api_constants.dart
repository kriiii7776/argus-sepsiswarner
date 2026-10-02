class ApiConstants {
  static String defaultBaseUrl = 'http://172.27.45.54:8000';
  static String defaultWsUrl = 'ws://172.27.45.54:8000/api/v1/ws/stream';

  static String wsStreamPath = '/api/v1/ws/stream';
  static String eventsVitalsPath = '/events/vitals';
  static String patientsPath = '/patients';

  static String getWsUrlFromBase(String baseUrl) {
    if (baseUrl.startsWith('http://')) {
      final host = baseUrl.substring(7);
      return 'ws://$host$wsStreamPath';
    } else if (baseUrl.startsWith('https://')) {
      final host = baseUrl.substring(8);
      return 'wss://$host$wsStreamPath';
    }
    return 'ws://$baseUrl$wsStreamPath';
  }
}
