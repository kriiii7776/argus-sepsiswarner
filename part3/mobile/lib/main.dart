import 'package:flutter/material.dart';
import 'core/constants/app_theme.dart';
import 'core/network/websocket_client.dart';
import 'presentation/state/app_state.dart';
import 'presentation/screens/main_navigation_screen.dart';

import 'core/services/notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final wsClient = WebSocketClient();
  final appState = AppState(wsClient: wsClient);

  await NotificationService.instance.initialize(
    onTap: (patientId) {
      appState.selectPatient(patientId);
    },
  );

  runApp(ArgusMobileApp(appState: appState));
}

class ArgusMobileApp extends StatelessWidget {
  final AppState appState;

  const ArgusMobileApp({super.key, required this.appState});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ARGUS Mobile Response',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: MainNavigationScreen(state: appState),
    );
  }
}
