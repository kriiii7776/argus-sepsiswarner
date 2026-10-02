import 'package:flutter_test/flutter_test.dart';
import 'package:argus_mobile/core/network/websocket_client.dart';

void main() {
  group('Connection State Tests', () {
    test('Verify ConnectionStatus enum string labels', () {
      expect(ConnectionStatus.connected.label, equals('Live'));
      expect(ConnectionStatus.reconnecting.label, equals('Reconnecting...'));
      expect(ConnectionStatus.disconnected.label, equals('Disconnected'));
      expect(ConnectionStatus.error.label, equals('Connection error'));
    });
  });
}
