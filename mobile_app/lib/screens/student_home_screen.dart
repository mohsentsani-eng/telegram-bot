import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class StudentHomeScreen extends StatefulWidget {
  const StudentHomeScreen({super.key});

  @override
  State<StudentHomeScreen> createState() => _StudentHomeScreenState();
}

class _StudentHomeScreenState extends State<StudentHomeScreen> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        body: SafeArea(
          child: CustomScrollView(
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 24),
                sliver: SliverList(
                  delegate: SliverChildListDelegate([
                    _topBar(),
                    const SizedBox(height: 22),
                    _welcomeCard(),
                    const SizedBox(height: 20),
                    _sectionTitle('برنامه امروز', 'مشاهده برنامه', onTap: () {}),
                    const SizedBox(height: 12),
                    _todayTask(),
                    const SizedBox(height: 22),
                    _sectionTitle('دسترسی سریع', 'همه امکانات'),
                    const SizedBox(height: 12),
                    _quickActions(),
                    const SizedBox(height: 22),
                    _dailyProgress(),
                    const SizedBox(height: 20),
                    _counselorCard(),
                    const SizedBox(height: 18),
                    _syncStatus(),
                  ]),
                ),
              ),
            ],
          ),
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _selectedIndex,
          onDestinationSelected: (value) => setState(() => _selectedIndex = value),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'خانه'),
            NavigationDestination(icon: Icon(Icons.calendar_month_outlined), label: 'برنامه'),
            NavigationDestination(icon: Icon(Icons.quiz_outlined), label: 'آزمون‌ها'),
            NavigationDestination(icon: Icon(Icons.insights_outlined), label: 'گزارش‌ها'),
            NavigationDestination(icon: Icon(Icons.person_outline), label: 'حساب من'),
          ],
        ),
      ),
    );
  }

  Widget _topBar() => Row(
    children: [
      Container(
        width: 44, height: 44,
        decoration: BoxDecoration(
          color: AppColors.sky,
          borderRadius: BorderRadius.circular(14),
        ),
        child: const Icon(Icons.spa_rounded, color: AppColors.primary, size: 25),
      ),
      const SizedBox(width: 10),
      const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('ترنم همدلی', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: AppColors.deepBlue)),
          Text('پیشرفت تحصیلی و حال خوب', style: TextStyle(fontSize: 10, color: AppColors.muted)),
        ],
      ),
      const Spacer(),
      IconButton.filledTonal(
        onPressed: () {},
        style: IconButton.styleFrom(backgroundColor: Colors.white),
        icon: const Icon(Icons.notifications_none_rounded, color: AppColors.ink),
      ),
    ],
  );

  Widget _welcomeCard() => Container(
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(24),
      gradient: const LinearGradient(
        begin: Alignment.topRight,
        end: Alignment.bottomLeft,
        colors: [AppColors.primary, AppColors.deepBlue],
      ),
      boxShadow: [
        BoxShadow(color: AppColors.primary.withValues(alpha: .16), blurRadius: 22, offset: const Offset(0, 10)),
      ],
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          const Expanded(child: Text('سلام، خوش اومدی 🌱', style: TextStyle(color: Colors.white, fontSize: 21, fontWeight: FontWeight.w800))),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: .14), borderRadius: BorderRadius.circular(15)),
            child: const Icon(Icons.waving_hand_rounded, color: Colors.white, size: 25),
          ),
        ]),
        const SizedBox(height: 8),
        const Text('قدم‌های کوچک امروز، پیشرفت‌های بزرگ فردا را می‌سازند.', style: TextStyle(color: Color(0xFFE5EEFF), fontSize: 13, height: 1.8)),
        const SizedBox(height: 18),
        Row(children: [
          const Icon(Icons.calendar_today_rounded, color: Colors.white70, size: 15),
          const SizedBox(width: 7),
          const Text('برای شروع، برنامه امروزت رو ببین', style: TextStyle(color: Colors.white, fontSize: 12)),
          const Spacer(),
          Icon(Icons.arrow_back_rounded, color: Colors.white.withValues(alpha: .9), size: 18),
        ]),
      ],
    ),
  );

  Widget _sectionTitle(String title, String action, {VoidCallback? onTap}) => Row(
    children: [
      Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: AppColors.ink)),
      const Spacer(),
      TextButton(onPressed: onTap, child: Text(action, style: const TextStyle(fontSize: 12, color: AppColors.primary, fontWeight: FontWeight.w700))),
    ],
  );

  Widget _todayTask() => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(children: [
        Container(
          width: 48, height: 48,
          decoration: BoxDecoration(color: const Color(0xFFFFF5E5), borderRadius: BorderRadius.circular(15)),
          child: const Icon(Icons.menu_book_rounded, color: Color(0xFFB7791F), size: 25),
        ),
        const SizedBox(width: 13),
        const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('اولین قدم مطالعه', style: TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)),
          SizedBox(height: 4),
          Text('برنامه اختصاصی تو اینجا نمایش داده می‌شود', style: TextStyle(fontSize: 11, color: AppColors.muted)),
        ])),
        const Icon(Icons.chevron_left_rounded, color: AppColors.muted),
      ]),
    ),
  );

  Widget _quickActions() => GridView.count(
    crossAxisCount: 2,
    shrinkWrap: true,
    physics: const NeverScrollableScrollPhysics(),
    mainAxisSpacing: 11,
    crossAxisSpacing: 11,
    childAspectRatio: 1.8,
    children: const [
      _ActionTile(icon: Icons.calendar_month_rounded, title: 'برنامه مطالعاتی', subtitle: 'برنامه امروزت', tint: Color(0xFFEAF3FF), iconColor: AppColors.primary),
      _ActionTile(icon: Icons.quiz_rounded, title: 'آزمون‌های من', subtitle: 'تمرین و ارزیابی', tint: Color(0xFFF1EDFF), iconColor: Color(0xFF7660B5)),
      _ActionTile(icon: Icons.timer_rounded, title: 'ساعت مطالعه', subtitle: 'ثبت فعالیت روزانه', tint: Color(0xFFFFF5E5), iconColor: Color(0xFFB7791F)),
      _ActionTile(icon: Icons.favorite_rounded, title: 'حال خوب من', subtitle: 'حال و انگیزه امروز', tint: Color(0xFFFFEDF0), iconColor: Color(0xFFC45B72)),
    ],
  );

  Widget _dailyProgress() => Card(
    child: Padding(
      padding: const EdgeInsets.all(17),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('پیشرفت امروز', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppColors.ink)),
        const SizedBox(height: 6),
        const Text('با هر قدم، به هدفت نزدیک‌تر می‌شی.', style: TextStyle(fontSize: 11, color: AppColors.muted)),
        const SizedBox(height: 14),
        ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: const LinearProgressIndicator(value: 0, minHeight: 9, backgroundColor: AppColors.sky, color: AppColors.primary),
        ),
        const SizedBox(height: 8),
        const Text('بعد از دریافت برنامه، میزان پیشرفتت اینجا نمایش داده می‌شود.', style: TextStyle(fontSize: 10, color: AppColors.muted)),
      ]),
    ),
  );

  Widget _counselorCard() => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(children: [
        Container(
          width: 45, height: 45,
          decoration: BoxDecoration(color: AppColors.sky, borderRadius: BorderRadius.circular(15)),
          child: const Icon(Icons.chat_bubble_outline_rounded, color: AppColors.primary),
        ),
        const SizedBox(width: 12),
        const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('همراهی مشاور', style: TextStyle(fontWeight: FontWeight.w800, color: AppColors.ink)),
          SizedBox(height: 4),
          Text('هر زمان نیاز داشتی، می‌تونی پیام بدی.', style: TextStyle(fontSize: 11, color: AppColors.muted)),
        ])),
        const Icon(Icons.arrow_back_ios_new_rounded, size: 15, color: AppColors.muted),
      ]),
    ),
  );

  Widget _syncStatus() => Container(
    padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 11),
    decoration: BoxDecoration(color: const Color(0xFFEAF6F0), borderRadius: BorderRadius.circular(13)),
    child: const Row(children: [
      Icon(Icons.cloud_done_outlined, color: AppColors.success, size: 17),
      SizedBox(width: 8),
      Expanded(child: Text('وضعیت همگام‌سازی پس از اتصال به حساب نمایش داده می‌شود.', style: TextStyle(fontSize: 10, color: AppColors.success))),
    ]),
  );
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({required this.icon, required this.title, required this.subtitle, required this.tint, required this.iconColor});
  final IconData icon;
  final String title;
  final String subtitle;
  final Color tint;
  final Color iconColor;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Row(children: [
        Container(
          width: 39, height: 39,
          decoration: BoxDecoration(color: tint, borderRadius: BorderRadius.circular(13)),
          child: Icon(icon, color: iconColor, size: 21),
        ),
        const SizedBox(width: 9),
        Expanded(child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppColors.ink)),
            const SizedBox(height: 3),
            Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9, color: AppColors.muted)),
          ],
        )),
      ]),
    ),
  );
}
