import 'package:flutter/material.dart';
import '../../core/constants/api_constants.dart';
import '../../core/constants/app_theme.dart';
import '../state/app_state.dart';
import '../widgets/connection_status_banner.dart';

class SettingsScreen extends StatefulWidget {
  final AppState state;

  const SettingsScreen({super.key, required this.state});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: ApiConstants.defaultBaseUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ConnectionStatusBanner(
          status: widget.state.connectionStatus,
          isStaleData: widget.state.isStaleData,
        ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                color: AppColors.surfaceDark,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'STAFF USER IDENTITY',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.blueAccent,
                        ),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        initialValue: widget.state.currentUserId,
                        decoration: const InputDecoration(
                          labelText: 'Active Clinician / Staff User',
                          border: OutlineInputBorder(),
                        ),
                        items: AppState.availableStaff.values.map((staff) {
                          return DropdownMenuItem<String>(
                            value: staff.userId,
                            child: Text(
                              '${staff.name} (${staff.role} - ${staff.unit})',
                              style: const TextStyle(color: Colors.white),
                            ),
                          );
                        }).toList(),
                        onChanged: (val) {
                          if (val != null) {
                            widget.state.setCurrentUser(val);
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  'Switched user to ${widget.state.currentStaff.name} (${widget.state.currentStaff.role})',
                                ),
                              ),
                            );
                          }
                        },
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Assigned Patients: ${widget.state.currentStaff.assignedPatients.join(", ")}',
                        style: const TextStyle(fontSize: 13, color: Colors.white70),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                color: AppColors.surfaceDark,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'SERVER CONFIGURATION',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.blueAccent,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _urlController,
                        decoration: const InputDecoration(
                          labelText: 'Backend Base URL (HTTP / REST)',
                          hintText: 'http://10.0.2.2:8000',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        icon: const Icon(Icons.save),
                        label: const Text('Update & Connect'),
                        onPressed: () {
                          final newUrl = _urlController.text.trim();
                          if (newUrl.isNotEmpty) {
                            widget.state.updateServerUrl(newUrl);
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Server URL updated to $newUrl')),
                            );
                          }
                        },
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Card(
                color: AppColors.surfaceDark,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'SYSTEM INFORMATION',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white70,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const ListTile(
                        dense: true,
                        title: Text('Application'),
                        subtitle: Text('ARGUS Mobile Alert System'),
                      ),
                      const ListTile(
                        dense: true,
                        title: Text('Version'),
                        subtitle: Text('1.0.0+1 (Part 3B Core)'),
                      ),
                      const ListTile(
                        dense: true,
                        title: Text('Target Platform'),
                        subtitle: Text('Android APK (Flutter + Dart)'),
                      ),
                      ListTile(
                        dense: true,
                        title: const Text('Stream Endpoint'),
                        subtitle: Text(ApiConstants.wsStreamPath),
                      ),
                    ],
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
