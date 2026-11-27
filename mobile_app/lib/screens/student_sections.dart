import 'dart:async';
import '../services/study_activity_store.dart';
import '../services/mobile_auth_service.dart';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class StudyPlanScreen extends StatefulWidget {
  const StudyPlanScreen({super.key});

  @override
  State<StudyPlanScreen> createState() => _StudyPlanScreenState();
}

class _StudyPlanScreenState extends State<StudyPlanScreen> {
  final _auth = MobileAuthService();
  Map<String, dynamic>? _plan;
  bool _loading = false;
  bool _offline = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (_loading) return;
    setState(() => _loading = true);
    try {
      final id = await _auth.cachedStudentId();
      if (id == null) throw StateError('حساب دانش‌آموز در دسترس نیست.');
      final cached = await _auth.cachedStudyPlan(id);
      if (!mounted) return;
      setState(() => _plan = cached);
      final plan = await _auth.fetchStudyPlan(id);
      if (mounted) setState(() { _plan = plan; _offline = false; });
    } catch (_) {
      final id = await _auth.cachedStudentId();
      if (mounted) setState(() {
        if (id == null) _plan = null;
        _offline = true;
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _time(int minutes) =>
      '${(minutes ~/ 60).toString().padLeft(2, '0')}:${(minutes % 60).toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final schedule = _plan?['schedule'] as List<dynamic>? ?? [];
    return Scaffold(
      appBar: AppBar(
        title: const Text('برنامه مطالعاتی'),
        actions: [
          IconButton(
            tooltip: 'دریافت دوباره برنامه',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        if (_loading) const LinearProgressIndicator(),
        if (_offline)
          Text(_plan == null ? 'دریافت برنامه ممکن نشد.' : 'نمایش آخرین برنامه ذخیره‌شده'),
        if (!_loading && !_offline && _plan == null)
          const Text('هنوز برنامه فعالی برای شما ثبت نشده است.'),
        if (_plan != null) Text(_plan?['title'] as String? ?? 'برنامه مطالعاتی'),
        for (final block in schedule.cast<List<dynamic>>())
          ListTile(
            title: Text('${block[0]} • ${block[3]}'),
            subtitle: Text('${_time(block[1] as int)} تا ${_time(block[2] as int)}'),
          ),
      ]),
    );
  }
}
class TestsScreen extends StatelessWidget {
  const TestsScreen({super.key});
  @override
  Widget build(BuildContext context) => const _SimpleStudentPage(title: 'آزمون‌های من', subtitle: 'تمرین کن، یاد بگیر و پیشرفتت رو ببین', icon: Icons.quiz_rounded, items: ['آزمون تمرینی ریاضی  •  ۱۵ سؤال','مرور علوم  •  ۱۰ سؤال','آزمون مهارت‌های یادگیری  •  دانلود نشده']);
}
class DailyReportScreen extends StatefulWidget {
  const DailyReportScreen({super.key});
  @override
  State<DailyReportScreen> createState() => _DailyReportScreenState();
}

class _DailyReportScreenState extends State<DailyReportScreen> with WidgetsBindingObserver {
  Timer? _retryTimer;
  final _store = StudyActivityStore();
  final _subject = TextEditingController();
  String _activityType = 'study';
  int _minutes = 45;
  int _tests = 0;
  int? _studentId;
  bool _saving = false;
  bool _syncing = false;
  String? _error;
  List<Map<String, dynamic>> _activities = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(_load().then((_) => _sync(quiet: true)));
    _startRetryTimer();
  }

  void _startRetryTimer() {
    _retryTimer?.cancel();
    _retryTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      unawaited(_sync(quiet: true));
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(_sync(quiet: true));
      _startRetryTimer();
    } else {
      _retryTimer?.cancel();
    }
  }

  Future<void> _load() async {
    try {
      final profile = await MobileAuthService().fetchStudentProfile();
      final studentId = (profile['student_id'] as num).toInt();
      final activities = await _store.read(studentId);
      if (mounted) setState(() {
        _studentId = studentId;
        _activities = activities;
        _error = null;
      });
    } catch (_) {
      final cached = await MobileAuthService().cachedStudentId();
      if (cached != null) {
        final activities = await _store.read(cached);
        if (mounted) setState(() {
          _studentId = cached;
          _activities = activities;
          _error = null;
        });
      } else if (mounted) {
        setState(() => _error = 'برای ثبت گزارش، یک بار با اینترنت مشخصات حساب را دریافت کنید.');
      }
    }
  }

  Future<void> _save() async {
    if (_studentId == null || _saving) return;
    setState(() => _saving = true);
    try {
      await _store.add(
        studentId: _studentId!,
        subject: _subject.text,
        activityType: _activityType,
        durationMinutes: _minutes,
        testCount: _tests,
      );
      final updated = await _store.read(_studentId!);
      if (!mounted) return;
      setState(() {
        _activities = updated;
        _error = null;
      });
      _subject.clear();
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('فعالیت روی گوشی ذخیره شد؛ هنوز به سرور ارسال نشده است.'),
      ));
      unawaited(_sync(quiet: true));
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Invalid argument(s): ', ''));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _sync({bool quiet = false}) async {
    if (!mounted || _studentId == null || _syncing) return;
    if (quiet && !_activities.any((item) => item['sync_state'] != 'synced')) return;
    setState(() => _syncing = true);
    try {
      final count = await MobileAuthService().syncStudyActivities(_studentId!, _store);
      final updated = await _store.read(_studentId!);
      if (!mounted) return;
      setState(() { _activities = updated; _error = null; });
      if (!quiet) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('$count فعالیت با سرور همگام شد.'),
      ));
    } catch (_) {
      if (mounted && !quiet) setState(() => _error =
          'ارسال کامل نشد. گزارش‌های تأییدنشده برای تلاش بعدی روی گوشی باقی ماندند.');
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  void dispose() {
    _retryTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    _subject.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('ثبت مطالعه'), backgroundColor: AppColors.canvas),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      const Text('مطالعه امروزت رو ثبت کن', style: TextStyle(
        fontSize: 19, fontWeight: FontWeight.w800, color: AppColors.ink)),
      const SizedBox(height: 12),
      const Card(child: Padding(padding: EdgeInsets.all(14),
        child: Text('فعالیت‌ها ابتدا روی گوشی ذخیره می‌شوند. با اتصال اینترنت، '
            'دکمه همگام‌سازی را بزنید. پیش از تأیید ارسال، برنامه را حذف نکنید.',
            style: TextStyle(fontSize: 12, height: 1.8)))),
      const SizedBox(height: 16),
      TextField(controller: _subject, maxLength: 80,
        decoration: const InputDecoration(labelText: 'نام درس', hintText: 'مثلاً زیست‌شناسی')),
      const SizedBox(height: 10),
      DropdownButtonFormField<String>(
        value: _activityType,
        decoration: const InputDecoration(labelText: 'نوع فعالیت'),
        items: const [
          DropdownMenuItem(value: 'study', child: Text('مطالعه')),
          DropdownMenuItem(value: 'practice', child: Text('حل تست و تمرین')),
          DropdownMenuItem(value: 'review', child: Text('مرور')),
          DropdownMenuItem(value: 'video', child: Text('فیلم آموزشی')),
        ],
        onChanged: (value) => setState(() => _activityType = value ?? 'study'),
      ),
      const SizedBox(height: 18),
      Text('مدت فعالیت: $_minutes دقیقه', style: const TextStyle(fontWeight: FontWeight.w700)),
      Slider(value: _minutes.toDouble(), min: 5, max: 180, divisions: 35,
        onChanged: (v) => setState(() => _minutes = v.round())),
      const SizedBox(height: 10),
      Text('تعداد تست: $_tests', style: const TextStyle(fontWeight: FontWeight.w700)),
      Slider(value: _tests.toDouble(), min: 0, max: 100, divisions: 100,
        onChanged: (v) => setState(() => _tests = v.round())),
      if (_error != null) ...[
        const SizedBox(height: 8),
        Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 12)),
        TextButton(onPressed: _load, child: const Text('تلاش مجدد برای دریافت حساب')),
      ],
      const SizedBox(height: 14),
      FilledButton.icon(
        onPressed: _studentId == null || _saving ? null : _save,
        icon: const Icon(Icons.save_rounded),
        label: Text(_saving ? 'در حال ذخیره...' : 'ذخیره روی گوشی'),
      ),
      const SizedBox(height: 12),
      OutlinedButton.icon(
        onPressed: _studentId == null || _syncing ? null : () => _sync(),
        icon: const Icon(Icons.sync_rounded),
        label: Text(_syncing ? 'در حال همگام‌سازی...' : 'ارسال گزارش‌های ذخیره‌شده به سرور'),
      ),
      const SizedBox(height: 24),
      Text('فعالیت‌های ثبت‌شده (${_activities.length})',
        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
      const SizedBox(height: 8),
      ..._activities.take(20).map((activity) => Card(child: ListTile(
        title: Text(activity['subject'] as String),
        subtitle: Text('${activity['duration_minutes']} دقیقه • '
          '${activity['test_count']} تست • ${activity['sync_state'] == 'synced' ? 'همگام‌شده' : 'در انتظار همگام‌سازی'}'),
        leading: const Icon(Icons.cloud_off_outlined, color: AppColors.primary),
      ))),
    ]),
  );
}

class WellbeingScreen extends StatefulWidget {
  const WellbeingScreen({super.key});
  @override
  State<WellbeingScreen> createState() => _WellbeingScreenState();
}
class _WellbeingScreenState extends State<WellbeingScreen> {
  int mood = 3;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('حال خوب من'), backgroundColor: AppColors.canvas),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      const Text('اینجا می‌تونی بدون قضاوت از حال امروزت بگی.', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: AppColors.ink)),
      const SizedBox(height: 18),
      const _OfflineNotice(),
      const SizedBox(height: 22),
      const Text('امروز چه حسی داری؟', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
      const SizedBox(height: 12),
      Wrap(spacing: 8, children: List.generate(4, (i) => ChoiceChip(label: Text(['😔 گرفته','😕 معمولی','🙂 خوب','😄 شاد'][i]), selected: mood == i + 1, onSelected: (_) => setState(() => mood = i + 1)))),
      const SizedBox(height: 22),
      const Text('این بخش برای شناخت بهتر حال روزانه توست و ابزار تشخیص پزشکی یا روان‌شناختی نیست. اگر نیاز به همراهی داری، می‌تونی با مشاورت ارتباط بگیری.', style: TextStyle(fontSize: 12, height: 1.9, color: AppColors.muted)),
      const SizedBox(height: 18),
      FilledButton(onPressed: () => ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('این فرم نمایشی است؛ ذخیره امن در مرحله بعد فعال می‌شود.'))), child: const Text('ثبت حال امروز')),
    ]),
  );
}
class _SimpleStudentPage extends StatelessWidget {
  const _SimpleStudentPage({required this.title, required this.subtitle, required this.icon, required this.items});
  final String title, subtitle;
  final IconData icon;
  final List<String> items;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('ترنم همدلی', style: TextStyle(fontWeight: FontWeight.w900, color: AppColors.deepBlue)), backgroundColor: AppColors.canvas),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      Row(children: [Icon(icon, color: AppColors.primary, size: 30), const SizedBox(width: 12), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: AppColors.ink)), Text(subtitle, style: const TextStyle(color: AppColors.muted, fontSize: 12))]))]),
      const SizedBox(height: 20),
      const _OfflineNotice(),
      const SizedBox(height: 14),
      ...items.map((item) => Card(margin: const EdgeInsets.only(bottom: 10), child: ListTile(leading: const CircleAvatar(backgroundColor: AppColors.sky, child: Icon(Icons.menu_book_rounded, color: AppColors.primary)), title: Text(item, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)), trailing: const Icon(Icons.chevron_left_rounded)))),
    ]),
  );
}
class _OfflineNotice extends StatelessWidget {
  const _OfflineNotice();
  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.all(13), decoration: BoxDecoration(color: const Color(0xFFEAF6F0), borderRadius: BorderRadius.circular(14)), child: const Row(children: [Icon(Icons.cloud_done_outlined, color: AppColors.success), SizedBox(width: 8), Expanded(child: Text('این بخش نمایشی است؛ ذخیره‌سازی امن و آفلاین هنوز فعال نشده است.', style: TextStyle(color: AppColors.success, fontSize: 11)))]));
}

class StudentProfileScreen extends StatefulWidget {
  const StudentProfileScreen({super.key});

  @override
  State<StudentProfileScreen> createState() => _StudentProfileScreenState();
}

class _StudentProfileScreenState extends State<StudentProfileScreen> {
  late Future<Map<String, dynamic>> _profile;

  @override
  void initState() {
    super.initState();
    _profile = MobileAuthService().fetchStudentProfile();
  }

  void _retry() => setState(() {
    _profile = MobileAuthService().fetchStudentProfile();
  });

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('حساب من'), backgroundColor: AppColors.canvas),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _profile,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.wifi_off_rounded, color: AppColors.muted, size: 42),
              const SizedBox(height: 12),
              const Text('دریافت مشخصات ممکن نشد. اتصال اینترنت را بررسی کنید.'),
              const SizedBox(height: 12),
              FilledButton(onPressed: _retry, child: const Text('تلاش دوباره')),
            ]),
          ));
        }
        final data = snapshot.data!;
        String value(String key) {
          final v = data[key]?.toString().trim() ?? '';
          return v.isEmpty ? 'ثبت نشده' : v;
        }
        final fullName = '${value('first_name')} ${value('last_name')}';
        return ListView(padding: const EdgeInsets.all(20), children: [
          Card(child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(children: [
              const CircleAvatar(radius: 30, backgroundColor: AppColors.sky,
                child: Icon(Icons.person_rounded, color: AppColors.primary, size: 32)),
              const SizedBox(height: 12),
              Text(fullName, textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
              const SizedBox(height: 5),
              const Text('اطلاعات تأییدشده حساب دانش‌آموز',
                style: TextStyle(fontSize: 12, color: AppColors.muted)),
            ]),
          )),
          const SizedBox(height: 14),
          _profileItem('پایه تحصیلی', value('grade')),
          _profileItem('رشته تحصیلی', value('track')),
          _profileItem('شهر', value('city')),
          const SizedBox(height: 18),
          const Text('این اطلاعات از پرونده ثبت‌شده شما در مرکز دریافت می‌شود. '
              'در صورت نیاز به اصلاح، با مرکز ترنم همدلی تماس بگیرید.',
              style: TextStyle(fontSize: 12, height: 1.8, color: AppColors.muted)),
        ]);
      },
    ),
  );

  Widget _profileItem(String label, String value) => Card(
    child: ListTile(
      title: Text(label, style: const TextStyle(color: AppColors.muted, fontSize: 12)),
      subtitle: Text(value, style: const TextStyle(fontWeight: FontWeight.w800)),
    ),
  );
}
