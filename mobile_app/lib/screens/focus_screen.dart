import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/focus_session.dart';
import '../theme/apex_components.dart';
import 'apex_dashboard.dart';

class FocusScreen extends StatefulWidget {
  const FocusScreen({super.key, required this.scope});

  final String scope;

  @override
  State<FocusScreen> createState() => _FocusScreenState();
}

class _FocusScreenState extends State<FocusScreen> with WidgetsBindingObserver {
  late final Future<SharedPreferences> _prefs;
  FocusSession? _session;
  Timer? _ticker;
  int _minutes = 25;
  bool _busy = true;
  bool _loadFailed = false;

  String get _key => 'apex360_focus_v1_${widget.scope}';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _prefs = SharedPreferences.getInstance();
    _load();
  }

  Future<void> _load() async {
    try {
      final raw = (await _prefs).getString(_key);
      final session = raw == null ? null : FocusSession.decode(raw);
      if (!mounted) return;
      setState(() {
        _session = session;
        _busy = false;
      });
      _refreshTicker();
    } catch (_) {
      if (mounted)
        setState(() {
          _busy = false;
          _loadFailed = true;
        });
    }
  }

  void _refreshTicker() {
    _ticker?.cancel();
    if (_session?.endsAt == null || _session!.remaining(DateTime.now()) == 0) {
      return;
    }
    _ticker = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {});
      if (_session!.remaining(DateTime.now()) == 0) timer.cancel();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      setState(() {});
      _refreshTicker();
    } else {
      _ticker?.cancel();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _ticker?.cancel();
    super.dispose();
  }

  Future<bool> _persist(FocusSession? next) async {
    if (_busy) return false;
    setState(() => _busy = true);
    try {
      final prefs = await _prefs;
      final saved = next == null
          ? await prefs.remove(_key)
          : await prefs.setString(_key, next.encode());
      if (!saved) throw StateError('Focus session could not be saved');
      if (!mounted) return false;
      setState(() => _session = next);
      _refreshTicker();
      return true;
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('ذخیرهٔ وضعیت تمرکز ممکن نشد. دوباره تلاش کن.'),
          ),
        );
      return false;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _discard() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('زمان‌سنج را بازنشانی کنیم؟'),
        content: const Text('زمان این نوبت از زمان‌سنج پاک می‌شود.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialog, false),
            child: const Text('ادامهٔ نوبت'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialog, true),
            child: const Text('بازنشانی'),
          ),
        ],
      ),
    );
    if (mounted && confirmed == true) await _persist(null);
  }

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final session = _session;
    final remaining = session?.remaining(now) ?? _minutes * 60;
    final elapsed = session?.elapsedMinutes(now) ?? 0;
    final complete = session != null && remaining == 0;
    final running = session?.endsAt != null && !complete;
    final clock = fa(
      '${(remaining ~/ 60).toString().padLeft(2, '0')}:${(remaining % 60).toString().padLeft(2, '0')}',
    );
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('زمان‌سنج مطالعه')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_loadFailed)
            const ApexSection(
              'خواندن زمان‌سنج ممکن نشد',
              detail: 'صفحه را دوباره باز کن.',
            )
          else if (_busy && session == null)
            const LinearProgressIndicator()
          else ...[
            ApexSection(
              complete
                  ? 'وقت یک نفس تازه'
                  : running
                  ? 'آوا همراه توست'
                  : session == null
                  ? 'یک نوبت تمرکز'
                  : 'مکث کوتاه',
              detail: complete
                  ? 'می‌توانی زمان را به گزارش مطالعه منتقل کنی.'
                  : 'یک کار را انتخاب کن و به خودت برای ادامه زمان بده.',
            ),
            const SizedBox(height: 4),
            LayoutBuilder(
              builder: (context, constraints) {
                final diameter = math.min(256.0, constraints.maxWidth);
                return Center(
                  child: SizedBox.square(
                    dimension: diameter,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        CircularProgressIndicator(
                          value: session == null
                              ? 0
                              : 1 - remaining / session.total,
                          strokeWidth: 9,
                          strokeCap: StrokeCap.round,
                          backgroundColor: colors.secondaryContainer,
                          semanticsLabel: 'پیشرفت نوبت تمرکز',
                        ),
                        Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              AvaCompanion(
                                celebrating: complete,
                                focused: running,
                                size: diameter * .36,
                              ),
                              SizedBox(
                                width: diameter * .72,
                                child: FittedBox(
                                  fit: BoxFit.scaleDown,
                                  child: Text(
                                    clock,
                                    textDirection: TextDirection.ltr,
                                    style: Theme.of(context)
                                        .textTheme
                                        .displaySmall
                                        ?.copyWith(fontWeight: FontWeight.w700),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
            const SizedBox(height: 26),
            if (session == null) ...[
              MinuteChoices(
                selected: _minutes,
                onSelect: (minutes) => setState(() => _minutes = minutes),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _busy
                    ? null
                    : () => _persist(
                        FocusSession.start(_minutes, DateTime.now()),
                      ),
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('شروع تمرکز'),
              ),
            ] else ...[
              if (!complete)
                FilledButton.icon(
                  icon: Icon(
                    running ? Icons.pause_rounded : Icons.play_arrow_rounded,
                  ),
                  label: Text(running ? 'مکث' : 'ادامهٔ تمرکز'),
                  onPressed: _busy
                      ? null
                      : () {
                          final now = DateTime.now();
                          _persist(
                            running ? session.pause(now) : session.resume(now),
                          );
                        },
                ),
              if (elapsed > 0)
                OutlinedButton.icon(
                  icon: const Icon(Icons.edit_note),
                  label: Text('انتقال ${fa(elapsed)} دقیقه به گزارش'),
                  onPressed: _busy
                      ? null
                      : () async {
                          if (!await _persist(null) || !context.mounted) return;
                          Navigator.of(context).pop(elapsed);
                        },
                ),
              TextButton(
                onPressed: _busy ? null : _discard,
                child: const Text('بازنشانی زمان‌سنج'),
              ),
            ],
          ],
        ],
      ),
    );
  }
}
