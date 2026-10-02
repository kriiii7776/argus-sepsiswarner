import 'package:flutter/material.dart';
import '../../core/constants/app_theme.dart';
import '../../core/network/websocket_client.dart';

class ConnectionStatusBanner extends StatelessWidget {
  final ConnectionStatus status;
  final bool isStaleData;

  const ConnectionStatusBanner({
    super.key,
    required this.status,
    required this.isStaleData,
  });

  @override
  Widget build(BuildContext context) {
    Color badgeColor;
    IconData iconData;

    switch (status) {
      case ConnectionStatus.connected:
        badgeColor = AppColors.connectedGreen;
        iconData = Icons.wifi;
        break;
      case ConnectionStatus.reconnecting:
        badgeColor = AppColors.reconnectingAmber;
        iconData = Icons.sync;
        break;
      case ConnectionStatus.disconnected:
      case ConnectionStatus.error:
        badgeColor = AppColors.disconnectedRed;
        iconData = Icons.wifi_off;
        break;
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          color: AppColors.surfaceDark,
          child: Row(
            children: [
              Icon(iconData, size: 16, color: badgeColor),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Status: ${status.label}',
                  style: TextStyle(
                    color: badgeColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'ARGUS CDS v1.0',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 11),
              ),
            ],
          ),
        ),
        if (isStaleData)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
            color: AppColors.disconnectedRed,
            child: const Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: Colors.white, size: 18),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Connection lost — displayed information may be stale.',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
