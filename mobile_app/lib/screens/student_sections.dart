import 'dart:async';
import '../services/study_activity_store.dart';
import '../services/mobile_auth_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/app_theme.dart';

class StudyPlanScreen extends StatefulWidget {
  const StudyPlanScreen({super.key, this.active = true});

  final bool active;

  @override
  State<StudyPlanScreen> createState() => _StudyPlanScreenState();
}

class _StudyPlanScreenState extends State<StudyPlanScreen> with WidgetsBindingObserver {
  final _auth = MobileAuthService();
  Map<String, dynamic>? _counselor;
  bool _loading = false;
  bool _offline = false;
  bool _confirming = false;
  String? _receiptError;

  @override
  void didUpdateWidget(covariant StudyPlanScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.active && !oldWidget.active) unawaited(_load());
  }

  Future<void> _confirm(int planId) async {
    if (_confirming || _loading) return;
    setState(() {
      _confirming = true;
      _receiptError = null;
    });
    try {
      final id = await _auth.cachedStudentId();
      if (id == null) throw StateError('Student session unavailable');
      final context = await _auth.confirmPlan(id, planId);
      if (mounted) setState(() => _counselor = context);
    } catch (_) {
      if (mounted) setState(() {
        _receiptError = 'تأیید دریافت انجام نشد. برنامه را تازه‌سازی و دوباره تلاش کن.';
      });
    } finally {
      if (mounted) setState(() => _confirming = false);
    }
  }


  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) unawaited(_load());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  Future<void> _load() async {
    if (!mounted || _loading || _confirming) return;
    setState(() {
      _loading = true;
      _receiptError = null;
    });
    try {
      final id = await _auth.cachedStudentId();
      if (id == null) throw StateError('حساب دانش‌آموز در دسترس نیست.');
      final cached = await _auth.cachedCounselor(id);
      if (!mounted) return;
      setState(() => _counselor = cached);
      final counselor = await _auth.fetchCounselor(id);
      if (mounted) setState(() { _counselor = counselor; _offline = false; });
    } catch (_) {
      final id = await _auth.cachedStudentId();
      if (mounted) setState(() {
        if (id == null) _counselor = null;
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
    final assignment = _counselor?['assignment'] as Map<String, dynamic>?;
    final plan = _counselor?['plan'] as Map<String, dynamic>?;
    final schedule = plan?['schedule'] as List<dynamic>? ?? [];
    return Scaffold(
      appBar: AppBar(
        title: const Text('برنامه مشاور'),
        actions: [
          IconButton(
            tooltip: 'دریافت دوباره برنامه',
            onPressed: _loading || _confirming ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        if (_loading) const LinearProgressIndicator(),
        if (_offline)
          Text(_counselor == null
              ? 'دریافت اطلاعات مشاور ممکن نشد.'
              : 'نمایش آخرین وضعیت ذخیره‌شده؛ سرور در دسترس نیست.'),
        if (assignment != null)
          Card(child: ListTile(
            leading: const Icon(Icons.person_outline_rounded),
            title: Text(assignment['name'] as String),
            subtitle: const Text('مشاور تخصیص‌یافته'),
          )),
        if (!_loading && !_offline && assignment == null)
          const Text('هنوز مشاوری به حساب شما تخصیص داده نشده است.'),
        if (assignment != null && plan == null)
          const Text('مشاور هنوز برنامه‌ای منتشر نکرده است.'),
        if (plan != null)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(plan['title'] as String, style: Theme.of(context).textTheme.titleLarge),
          ),
        for (final block in schedule.cast<List<dynamic>>())
          ListTile(
            title: Text('${block[0]} • ${block[3]}'),
            subtitle: Text('${_time(block[1] as int)} تا ${_time(block[2] as int)}'),
          ),
        if (plan != null)
          if (plan['received_at'] != null)
            const ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.check_circle_outline),
              title: Text('دریافت برنامه تأیید شده است'),
            )
          else
            OutlinedButton.icon(
              onPressed: _loading || _confirming || _offline ? null : () => _confirm(plan['id'] as int),
              icon: const Icon(Icons.download_done_rounded),
              label: Text(_confirming ? 'در حال تأیید…' : 'تأیید دریافت برنامه'),
            ),
        if (_receiptError != null) Text(_receiptError!),
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
  const DailyReportScreen({super.key, this.active = true, this.onActivitiesChanged});

  final bool active;
  final ValueChanged<List<Map<String, dynamic>>>? onActivitiesChanged;
  @override
  State<DailyReportScreen> createState() => _DailyReportScreenState();
}

class _DailyReportScreenState extends State<DailyReportScreen> with WidgetsBindingObserver {
  Timer? _retryTimer;
  final _store = StudyActivityStore();
  final _subject = TextEditingController();
  String _activityType = 'study';
  final _minutes = TextEditingController(text: '45');
  final _tests = TextEditingController(text: '0');
  List<Map<String, dynamic>> _feedback = [];
  bool _feedbackLoading = false;
  bool _feedbackUnavailable = false;
  int? _studentId;
  bool _saving = false;
  bool _syncing = false;
  String? _error;
  bool _retryNeeded = false;
  int get _pending => _activities.where((item) => item['sync_state'] != 'synced').length;
  List<Map<String, dynamic>> _activities = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(_load().then((_) => _sync(quiet: true)));
    _startRetryTimer();
  }

  @override
  void didUpdateWidget(covariant DailyReportScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.active && !oldWidget.active) unawaited(_loadFeedback());
  }

  Future<void> _loadFeedback() async {
    final id = _studentId;
    if (!mounted || id == null || _feedbackLoading) return;
    setState(() => _feedbackLoading = true);
    try {
      final feedback = await MobileAuthService().fetchReportFeedback(id);
      if (mounted) setState(() {
        _feedback = feedback;
        _feedbackUnavailable = false;
      });
    } catch (_) {
      if (mounted) setState(() => _feedbackUnavailable = true);
    } finally {
      if (mounted) setState(() => _feedbackLoading = false);
    }
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
      if (widget.active) unawaited(_loadFeedback());
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
      if (mounted) widget.onActivitiesChanged?.call(activities);
      if (mounted) setState(() {
        _studentId = studentId;
        _activities = activities;
        _error = null;
      });
      if (widget.active) unawaited(_loadFeedback());
    } catch (_) {
      final cached = await MobileAuthService().cachedStudentId();
      if (cached != null) {
        final activities = await _store.read(cached);
        if (mounted) widget.onActivitiesChanged?.call(activities);
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
        durationMinutes: int.tryParse(_minutes.text) ?? 0,
        testCount: int.tryParse(_tests.text) ?? -1,
      );
      final updated = await _store.read(_studentId!);
      if (!mounted) return;
      setState(() {
        _activities = updated;
        _error = null;
      });
      widget.onActivitiesChanged?.call(updated);
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
    if (_pending == 0) return;
    setState(() => _syncing = true);
    try {
      final count = await MobileAuthService().syncStudyActivities(_studentId!, _store);
      final updated = await _store.read(_studentId!);
      if (!mounted) return;
      setState(() { _activities = updated; _retryNeeded = false; });
      widget.onActivitiesChanged?.call(updated);
      if (widget.active) unawaited(_loadFeedback());
      if (!quiet) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('$count فعالیت با سرور همگام شد.'),
      ));
    } catch (_) {
      final updated = await _store.read(_studentId!);
      if (mounted) setState(() {
        _activities = updated;
        _retryNeeded = true;
      });
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  void dispose() {
    _retryTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    _subject.dispose();
    _minutes.dispose();
    _tests.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('ثبت مطالعه'), backgroundColor: AppColors.canvas),
    body: ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 10), children: [
      Card(child: ListTile(
        leading: Icon(_retryNeeded ? Icons.cloud_off_outlined : Icons.cloud_sync_outlined),
        title: Text(_syncing ? 'در حال ارسال' : _pending > 0
            ? '$_pending گزارش در صف ارسال'
            : _activities.isEmpty ? 'هنوز گزارشی ثبت نشده' : 'ارسال گزارش‌ها تأیید شده'),
        subtitle: Text(_retryNeeded
            ? 'ارسال در آخرین تلاش کامل نشد. گزارش‌ها روی گوشی محفوظ‌اند.'
            : 'هنگام باز بودن برنامه، ارسال دوباره به‌صورت خودکار انجام می‌شود.'),
      )),
      const SizedBox(height: 16),
      TextField(controller: _subject, maxLength: 80,
        decoration: const InputDecoration(labelText: 'نام درس', hintText: 'مثلاً زیست‌شناسی', counterText: '')),
      const SizedBox(height: 10),
      DropdownButtonFormField<String>(
        initialValue: _activityType,
        decoration: const InputDecoration(labelText: 'نوع فعالیت'),
        items: const [
          DropdownMenuItem(value: 'study', child: Text('مطالعه')),
          DropdownMenuItem(value: 'practice', child: Text('حل تست و تمرین')),
          DropdownMenuItem(value: 'review', child: Text('مرور')),
          DropdownMenuItem(value: 'video', child: Text('فیلم آموزشی')),
        ],
        onChanged: (value) => setState(() => _activityType = value ?? 'study'),
      ),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: _numberField(_minutes, 'دقیقه مطالعه')),
        const SizedBox(width: 10),
        Expanded(child: _numberField(_tests, 'تعداد تست')),
      ]),
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
        onPressed: _studentId == null || _syncing || _pending == 0 ? null : () => _sync(),
        icon: const Icon(Icons.sync_rounded),
        label: Text(_syncing ? 'در حال همگام‌سازی...' : 'ارسال گزارش‌های ذخیره‌شده به سرور'),
      ),
      const SizedBox(height: 16),
      Row(children: [
        Expanded(child: Text('بازخورد مشاور', style: Theme.of(context).textTheme.titleMedium)),
        IconButton(
          tooltip: 'دریافت بازخورد',
          onPressed: _studentId == null || _feedbackLoading ? null : _loadFeedback,
          icon: const Icon(Icons.refresh),
        ),
      ]),
      if (_feedbackLoading) const LinearProgressIndicator(),
      if (_feedbackUnavailable) const Text('تازه‌سازی بازخورد ممکن نشد.'),
      if (_feedback.isEmpty && !_feedbackLoading && !_feedbackUnavailable)
        const Text('هنوز بازخوردی دریافت نشده است.'),
      for (final item in _feedback)
        Card(child: ListTile(
          leading: const Icon(Icons.chat_bubble_outline),
          title: Text('${item['subject']} · ${item['counselor_name']}'),
          subtitle: Text(item['message'] as String),
        )),
      const SizedBox(height: 24),
      Text('فعالیت‌های ثبت‌شده (${_activities.length})',
        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
      const SizedBox(height: 8),
      for (final activity in _activities.take(20))
        Card(child: ListTile(
          title: Text(activity['subject'] as String),
          subtitle: Text('${activity['duration_minutes']} دقیقه • ${activity['test_count']} تست'),
          leading: Icon(activity['sync_state'] == 'synced'
              ? Icons.cloud_done_outlined : Icons.schedule_rounded),
          trailing: Text(activity['sync_state'] == 'synced'
              ? 'تأیید سرور' : 'در صف ارسال'),
        )),
    ]),
  );

  Widget _numberField(TextEditingController controller, String label) => TextField(
    controller: controller,
    keyboardType: TextInputType.number,
    inputFormatters: [
      TextInputFormatter.withFunction((oldValue, newValue) {
        final text = newValue.text.replaceAllMapped(RegExp(r'[۰-۹٠-٩]'), (match) {
          final digit = match[0]!.codeUnitAt(0);
          return (digit >= 0x06f0 ? digit - 0x06f0 : digit - 0x0660).toString();
        });
        return newValue.copyWith(text: text);
      }),
      FilteringTextInputFormatter.digitsOnly,
      LengthLimitingTextInputFormatter(4),
    ],
    decoration: InputDecoration(labelText: label),
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
