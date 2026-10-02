import 'package:flutter/material.dart';
import '../state/app_state.dart';
import 'icu_overview_screen.dart';
import 'alert_center_screen.dart';
import 'immediate_review_screen.dart';
import 'settings_screen.dart';
import '../../core/constants/app_theme.dart';

class MainNavigationScreen extends StatefulWidget {
  final AppState state;

  const MainNavigationScreen({super.key, required this.state});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;

  void _onSelectPatient(String patientId) {
    widget.state.selectPatient(patientId);
    setState(() {
      _currentIndex = 2; // Jump to Patient View (Immediate Review)
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.state,
      builder: (context, _) {
        final urgentBadge = widget.state.urgentPatients.length;

        Widget body;
        switch (_currentIndex) {
          case 0:
            body = IcuOverviewScreen(
              state: widget.state,
              onSelectPatient: _onSelectPatient,
            );
            break;
          case 1:
            body = AlertCenterScreen(
              state: widget.state,
              onSelectPatient: _onSelectPatient,
            );
            break;
          case 2:
            if (widget.state.selectedPatientId != null) {
              body = ImmediateReviewScreen(
                state: widget.state,
                patientId: widget.state.selectedPatientId!,
                onBack: () {
                  setState(() {
                    _currentIndex = 0;
                  });
                },
              );
            } else if (widget.state.allPatients.isNotEmpty) {
              body = ImmediateReviewScreen(
                state: widget.state,
                patientId: widget.state.allPatients.first.patientId,
                onBack: () {
                  setState(() {
                    _currentIndex = 0;
                  });
                },
              );
            } else {
              body = const Center(
                child: Text(
                  'No patient selected.',
                  style: TextStyle(color: Colors.white54),
                ),
              );
            }
            break;
          case 3:
            body = SettingsScreen(state: widget.state);
            break;
          default:
            body = IcuOverviewScreen(
              state: widget.state,
              onSelectPatient: _onSelectPatient,
            );
        }

        return Scaffold(
          appBar: _currentIndex == 2
              ? null
              : AppBar(
                  title: const Text('ARGUS Clinical Alert System'),
                  backgroundColor: AppColors.surfaceDark,
                ),
          body: SafeArea(child: body),
          bottomNavigationBar: BottomNavigationBar(
            currentIndex: _currentIndex,
            onTap: (index) {
              setState(() {
                _currentIndex = index;
              });
            },
            type: BottomNavigationBarType.fixed,
            backgroundColor: AppColors.surfaceDark,
            selectedItemColor: Colors.blueAccent,
            unselectedItemColor: Colors.white54,
            items: [
              const BottomNavigationBarItem(
                icon: Icon(Icons.grid_view),
                label: 'ICU Overview',
              ),
              BottomNavigationBarItem(
                icon: Badge(
                  label: Text('$urgentBadge'),
                  isLabelVisible: urgentBadge > 0,
                  child: const Icon(Icons.notifications_active),
                ),
                label: 'Alerts',
              ),
              const BottomNavigationBarItem(
                icon: Icon(Icons.person_search),
                label: 'Patient',
              ),
              const BottomNavigationBarItem(
                icon: Icon(Icons.settings),
                label: 'Settings',
              ),
            ],
          ),
        );
      },
    );
  }
}
