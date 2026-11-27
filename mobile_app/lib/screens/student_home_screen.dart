import 'package:flutter/material.dart';
import 'package:shamsi_date/shamsi_date.dart';
import '../services/mobile_auth_service.dart';
import '../theme/app_theme.dart';
import 'student_sections.dart';
import 'apex_demo_screen.dart';
import 'apex_dashboard.dart';

class StudentHomeScreen extends StatefulWidget {
  const StudentHomeScreen({super.key, required this.onLoggedOut});
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
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('خروج امن کامل نشد. اتصال اینترنت را بررسی و دوباره تلاش کنید.'),
        ));
      }
    } finally {
      if (mounted) setState(() => _loggingOut = false);
    }
  }


  void _goToTab(int index) => setState(() => _selectedIndex = index);

  void _openWellbeing() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const WellbeingScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[
      _homePage(),
      StudyPlanScreen(active: _selectedIndex == 1),
      const TestsScreen(),
      DailyReportScreen(
        active: _selectedIndex == 3,
        onActivitiesChanged: (activities) => setState(() => _activities = activities),
      ),
      const StudentProfileScreen(),
    ];

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        body: IndexedStack(
          index: _selectedIndex,
          children: pages,
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: _goToTab,
          destinations: const [
            NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'خانه'),
            NavigationDestination(icon: Icon(Icons.calendar_month_outlined), label: 'برنامه مشاور'),
            NavigationDestination(icon: Icon(Icons.quiz_outlined), label: 'آزمون‌ها'),
            NavigationDestination(icon: Icon(Icons.insights_outlined), label: 'گزارش‌ها'),
            NavigationDestination(icon: Icon(Icons.person_outline), label: 'حساب من'),
          ],
        ),
      ),
    );
  }

  Widget _homePage() {
    final theme = Theme.of(context);
    final today = DateTime.now();
    final minutesByDay = <DateTime, int>{};
    var todayTests = 0;
    for (final activity in _activities) {
      final date = DateTime.tryParse(activity['created_at'] as String? ?? '')?.toLocal();
      if (date == null) continue;
      final day = DateUtils.dateOnly(date);
      minutesByDay.update(day, (value) => value + (activity['duration_minutes'] as int),
          ifAbsent: () => activity['duration_minutes'] as int);
      if (DateUtils.isSameDay(today, day)) todayTests += activity['test_count'] as int;
    }
    final todayMinutes = minutesByDay[DateUtils.dateOnly(today)] ?? 0;
    final guidance = todayMinutes > 0
        ? 'مطالعه امروزت ثبت شده. اگر انرژی داری، یک مرور کوتاه کافی است.'
        : 'از یک درس که می‌شناسی شروع کن. یک مرور کوتاه هم حساب می‌شود.';

    return SafeArea(
      bottom: false,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
        children: [
          Row(children: [
            Expanded(child: Text('Apex360', style: theme.textTheme.headlineSmall)),
            if (MobileAuthService.isLocalTest) const Chip(label: Text('حساب آزمایشی')),
            IconButton(
              tooltip: 'خروج از حساب',
              onPressed: _loggingOut ? null : _logout,
              icon: const Icon(Icons.logout_rounded),
            ),
          ]),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: AppColors.apexGradient,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                AvaCompanion(celebrating: todayMinutes > 0),
                const SizedBox(width: 12),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('آوا، همراه مطالعه‌ات', style: theme.textTheme.titleLarge?.copyWith(color: Colors.white)),
                  Text(guidance, style: const TextStyle(color: Colors.white, height: 1.6)),
                ])),
              ]),
              TextButton.icon(
                style: TextButton.styleFrom(foregroundColor: const Color(0xFFAAEEE2)),
                onPressed: () => showAva(context, guidance: guidance,
                    onPlan: () => _goToTab(1), onReport: () => _goToTab(3)),
                icon: const Icon(Icons.auto_awesome_rounded),
                label: const Text('از آوا کمک بگیر'),
              ),
            ]),
          ),
          const SizedBox(height: 14),
          Text('هدف امروز', style: theme.textTheme.titleLarge),
          const SizedBox(height: 6),
          Card(child: ListTile(
            leading: Icon(todayMinutes > 0 ? Icons.check_circle_outline : Icons.flag_outlined),
            title: Text(todayMinutes > 0 ? '$todayMinutes دقیقه مطالعه · $todayTests تست'
                : 'یک فعالیت کوتاه برای شروع'),
            subtitle: Text(todayMinutes > 0 ? 'نشان امروز · یک قدم برداشتی' : 'فعالیت را از برنامه مشاور یا برنامه شخصی انتخاب کن.'),
          )),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 6, children: [
            FilledButton.icon(
              onPressed: () => _goToTab(3),
              icon: const Icon(Icons.edit_note_rounded),
              label: const Text('ثبت مطالعه'),
            ),
            OutlinedButton.icon(
              onPressed: () => _goToTab(1),
              icon: const Icon(Icons.event_available_outlined),
              label: const Text('برنامه مشاور'),
            ),
          ]),
          const SizedBox(height: 12),
          ApexWeekChart(
            title: 'مطالعه در هفت روز گذشته',
            unit: 'دقیقه',
            days: List.generate(7, (index) {
              final day = DateTime(today.year, today.month, today.day - (6 - index));
              return (label: Jalali.fromDateTime(day).day.toString(), value: minutesByDay[day] ?? 0);
            }),
          ),
          const SizedBox(height: 6),
          ListTile(
            leading: const Icon(Icons.spa_outlined),
            title: const Text('حال خوب من'),
            onTap: _openWellbeing,
          ),
          ListTile(
            leading: const Icon(Icons.phone_android_rounded),
            title: const Text('باز کردن داشبورد آفلاین'),
            onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
              builder: (_) => const ApexDemoScreen(),
            )),
          ),
        ],
      ),
    );
  }
}
