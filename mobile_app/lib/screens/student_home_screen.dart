import 'package:flutter/material.dart';
import 'package:shamsi_date/shamsi_date.dart';

import '../services/mobile_auth_service.dart';
import '../theme/apex_components.dart';
import '../services/study_momentum.dart';
import 'student_sections.dart';
import 'apex_demo_screen.dart';
import 'apex_dashboard.dart';

class StudentHomeScreen extends StatefulWidget {
  const StudentHomeScreen({
    super.key,
    required this.onLoggedOut,
    this.onThemeChanged,
  });
  final ValueChanged<bool>? onThemeChanged;
  final VoidCallback onLoggedOut;

  @override
  State<StudentHomeScreen> createState() => _StudentHomeScreenState();
}

class _StudentHomeScreenState extends State<StudentHomeScreen> {
  int _selectedIndex = 0;
  bool _loggingOut = false;
  List<Map<String, dynamic>> _activities = [];

  Future<void> _logout() async {
    if (_loggingOut) return;
    setState(() => _loggingOut = true);
    try {
      await MobileAuthService().logout();
      if (mounted) widget.onLoggedOut();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'خروج امن کامل نشد. اتصال اینترنت را بررسی و دوباره تلاش کنید.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _loggingOut = false);
    }
  }

  void _goToTab(int index) => setState(() => _selectedIndex = index);

  void _openWellbeing() {
    Navigator.of(context)
        .push(MaterialPageRoute<void>(builder: (_) => const WellbeingScreen()));
  }

  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[
      _homePage(),
      StudyPlanScreen(active: _selectedIndex == 1, onPersonal: _openPersonal),
      const TestsScreen(),
      DailyReportScreen(
        active: _selectedIndex == 3,
        onActivitiesChanged: (activities) =>
            setState(() => _activities = activities),
      ),
      StudentProfileScreen(
        onLoggedOut: _loggingOut ? null : _logout,
        onThemeChanged: widget.onThemeChanged,
      ),
    ];

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        body: IndexedStack(index: _selectedIndex, children: pages),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: _goToTab,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded),
              label: 'خانه',
            ),
            NavigationDestination(
              icon: Icon(Icons.calendar_month_outlined),
              label: 'برنامه',
            ),
            NavigationDestination(
              icon: Icon(Icons.quiz_outlined),
              label: 'آزمون‌ها',
            ),
            NavigationDestination(
              icon: Icon(Icons.insights_outlined),
              label: 'گزارش',
            ),
            NavigationDestination(
              icon: Icon(Icons.person_outline),
              label: 'حساب من',
            ),
          ],
        ),
      ),
    );
  }

  void _openPersonal() => Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => ApexDemoScreen(onThemeChanged: widget.onThemeChanged),
    ),
  );

  Widget _homePage() {
    final now = DateTime.now();
    final jalali = Jalali.fromDateTime(now);
    final entries = <StudyEntry>[
      for (final row in _activities)
        if (DateTime.tryParse(row['created_at'] as String? ?? '')?.toLocal()
            case final DateTime date)
          (
            day: date,
            minutes: row['duration_minutes'] as int,
            tests: row['test_count'] as int,
          ),
    ];
    final momentum = StudyMomentum(entries, now);
    final active = momentum.todayMinutes > 0 || momentum.todayTests > 0;
    final pending = _activities
        .where((activity) => activity['sync_state'] != 'synced')
        .length;
    final minutesByDay = <DateTime, int>{};
    for (final entry in entries) {
      minutesByDay.update(
        DateUtils.dateOnly(entry.day),
        (value) => value + entry.minutes,
        ifAbsent: () => entry.minutes,
      );
    }
    return SafeArea(
      bottom: false,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
        children: [
          Row(
            children: [
              const Expanded(
                child: ApexSection('مسیر مطالعه', detail: 'Apex360'),
              ),
              if (MobileAuthService.isLocalTest)
                const Chip(label: Text('حساب آزمایشی')),
              IconButton(
                tooltip: 'پیشرفت مطالعه',
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => Scaffold(
                      appBar: AppBar(title: const Text('پیشرفت مطالعه')),
                      body: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          StudyAchievements(momentum: momentum),
                          ApexWeekChart(
                            title: 'مطالعه در هفت روز گذشته',
                            unit: 'دقیقه',
                            days: List.generate(7, (index) {
                              final day = DateTime(
                                now.year,
                                now.month,
                                now.day - 6 + index,
                              );
                              return (
                                label: Jalali.fromDateTime(day).day.toString(),
                                value: minutesByDay[day] ?? 0,
                              );
                            }),
                          ),
                          ApexWeekChart(
                            title: 'تمرین در هفت روز گذشته',
                            unit: 'تست',
                            days: List.generate(7, (index) {
                              final day = DateTime(
                                now.year,
                                now.month,
                                now.day - 6 + index,
                              );
                              final tests = entries
                                  .where(
                                    (row) => DateUtils.isSameDay(row.day, day),
                                  )
                                  .fold(0, (n, row) => n + row.tests);
                              return (
                                label: Jalali.fromDateTime(day).day.toString(),
                                value: tests,
                              );
                            }),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                icon: const Icon(Icons.insights_rounded),
              ),
            ],
          ),
          Text(fa('${jalali.year}/${jalali.month}/${jalali.day}')),
          const SizedBox(height: 8),
          AvaHero(
            title: active ? 'قدم امروز ثبت شد' : 'آماده‌ای شروع کنیم؟',
            guidance: active
                ? 'اگر انرژی داری، یک مرور کوتاه کافیه.'
                : 'یک درس آشنا بردار و از یک مرور کوتاه شروع کن.',
            celebrating: active,
            onPlan: () => _goToTab(1),
            onReport: () => _goToTab(3),
          ),
          MissionBoard(momentum: momentum),
          if (pending > 0)
            Card(
              child: ListTile(
                leading: const Icon(Icons.cloud_upload_outlined),
                title: Text('${fa(pending)} گزارش در صف ارسال'),
                onTap: () => _goToTab(3),
              ),
            ),
          const ApexSection('ادامهٔ مسیر'),
          Card(
            child: ListTile(
              leading: const Icon(Icons.event_available_rounded),
              title: const Text('برنامه مشاور'),
              trailing: const Icon(Icons.chevron_left),
              onTap: () => _goToTab(1),
            ),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.spa_outlined),
              title: const Text('حال خوب من'),
              onTap: _openWellbeing,
            ),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.phone_android_rounded),
              title: const Text('باز کردن داشبورد آفلاین'),
              onTap: _openPersonal,
            ),
          ),
        ],
      ),
    );
  }
}
