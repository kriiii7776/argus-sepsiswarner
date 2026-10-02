import 'package:flutter_test/flutter_test.dart';
import 'package:argus_mobile/main.dart';
import 'package:argus_mobile/core/network/websocket_client.dart';
import 'package:argus_mobile/presentation/state/app_state.dart';

void main() {
  testWidgets('ARGUS Mobile Application smoke test', (WidgetTester tester) async {
    final wsClient = WebSocketClient();
    final appState = AppState(wsClient: wsClient);

    await tester.pumpWidget(ArgusMobileApp(appState: appState));

    expect(find.text('ARGUS Clinical Alert System'), findsOneWidget);
    expect(find.text('ICU Overview'), findsWidgets);

    appState.dispose();
    wsClient.dispose();
    await tester.pumpAndSettle();
  });
}
