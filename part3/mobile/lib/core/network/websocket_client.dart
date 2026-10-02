import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../constants/api_constants.dart';

enum ConnectionStatus {
  connected,
  reconnecting,
  disconnected,
  error;

  String get label {
    switch (this) {
      case ConnectionStatus.connected:
        return 'Live';
      case ConnectionStatus.reconnecting:
        return 'Reconnecting...';
      case ConnectionStatus.disconnected:
        return 'Disconnected';
      case ConnectionStatus.error:
        return 'Connection error';
    }
  }
}

class WebSocketClient extends ChangeNotifier {
  String _wsUrl;
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _reconnectTimer;
  Timer? _pingTimer;

  ConnectionStatus _status = ConnectionStatus.disconnected;
  DateTime? _lastConnectedTime;
  DateTime? _lastDisconnectedTime;
  int _reconnectAttempts = 0;
  bool _isDisposed = false;

  final StreamController<Map<String, dynamic>> _messageController =
      StreamController<Map<String, dynamic>>.broadcast();

  WebSocketClient({String? serverUrl, String? userId})
      : _wsUrl = _buildWsUrl(serverUrl ?? ApiConstants.defaultWsUrl, userId);

  static String _buildWsUrl(String baseWsUrl, String? userId) {
    if (userId == null || userId.isEmpty) return baseWsUrl;
    final uri = Uri.parse(baseWsUrl);
    final query = Map<String, String>.from(uri.queryParameters);
    query['user_id'] = userId;
    return uri.replace(queryParameters: query).toString();
  }

  ConnectionStatus get status => _status;
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;
  DateTime? get lastConnectedTime => _lastConnectedTime;
  DateTime? get lastDisconnectedTime => _lastDisconnectedTime;

  bool get isStaleData {
    if (_status == ConnectionStatus.connected) return false;
    if (_lastDisconnectedTime == null) return false;
    return DateTime.now().difference(_lastDisconnectedTime!).inSeconds > 15;
  }

  void updateServerUrl(String newBaseUrl, {String? userId}) {
    final baseWsUrl = ApiConstants.getWsUrlFromBase(newBaseUrl);
    final newWsUrl = _buildWsUrl(baseWsUrl, userId);
    if (_wsUrl != newWsUrl) {
      _wsUrl = newWsUrl;
      disconnect();
      connect();
    }
  }

  void connect() {
    if (_isDisposed) return;
    if (_status == ConnectionStatus.connected) return;

    _setStatus(_reconnectAttempts > 0
        ? ConnectionStatus.reconnecting
        : ConnectionStatus.disconnected);

    try {
      final uri = Uri.parse(_wsUrl);
      _channel = WebSocketChannel.connect(uri);

      _subscription = _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _onDone,
        cancelOnError: true,
      );

      _setStatus(ConnectionStatus.connected);
      _lastConnectedTime = DateTime.now();
      _reconnectAttempts = 0;
      _startPingLoop();
    } catch (e) {
      developer.log('WebSocket connection error: $e', name: 'WebSocketClient');
      _setStatus(ConnectionStatus.error);
      _scheduleReconnect();
    }
  }

  void _onMessage(dynamic message) {
    if (message is! String) return;
    if (message.trim().isEmpty) return;

    try {
      final decoded = json.decode(message);
      if (decoded is Map<String, dynamic>) {
        if (decoded['type'] == 'pong') return;
        _messageController.add(decoded);
      }
    } catch (e) {
      developer.log('Malformed WS JSON skipped: $e', name: 'WebSocketClient');
    }
  }

  void _onError(dynamic error) {
    developer.log('WebSocket error: $error', name: 'WebSocketClient');
    _setStatus(ConnectionStatus.error);
    _scheduleReconnect();
  }

  void _onDone() {
    developer.log('WebSocket done/closed', name: 'WebSocketClient');
    _lastDisconnectedTime = DateTime.now();
    _setStatus(ConnectionStatus.disconnected);
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_isDisposed) return;
    _pingTimer?.cancel();
    _subscription?.cancel();
    _subscription = null;
    _channel = null;

    _reconnectAttempts++;
    final backoffSeconds = _getBackoffSeconds(_reconnectAttempts);

    _setStatus(ConnectionStatus.reconnecting);
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: backoffSeconds), () {
      if (!_isDisposed) {
        connect();
      }
    });
  }

  int _getBackoffSeconds(int attempt) {
    final list = [1, 2, 4, 8, 16, 30];
    if (attempt <= list.length) {
      return list[attempt - 1];
    }
    return 30;
  }

  void _startPingLoop() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(const Duration(seconds: 20), (timer) {
      if (_status == ConnectionStatus.connected && _channel != null) {
        try {
          _channel!.sink.add(json.encode({'type': 'ping'}));
        } catch (_) {}
      }
    });
  }

  void disconnect() {
    _reconnectTimer?.cancel();
    _pingTimer?.cancel();
    _subscription?.cancel();
    _channel?.sink.close();
    _subscription = null;
    _channel = null;
    _setStatus(ConnectionStatus.disconnected);
  }

  void _setStatus(ConnectionStatus newStatus) {
    if (_status != newStatus) {
      _status = newStatus;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    disconnect();
    _messageController.close();
    super.dispose();
  }
}
