import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../theme/apex_components.dart';

class WellbeingScreen extends StatefulWidget {
  const WellbeingScreen({super.key, required this.scope});

  final String scope;

  @override
  State<WellbeingScreen> createState() => _WellbeingScreenState();
}

class _WellbeingScreenState extends State<WellbeingScreen> {
  static const _storage = FlutterSecureStorage();
  static const _moods = [
    (
      Icons.sentiment_dissatisfied_rounded,
      'دل‌گرفته',
      'امروز می‌توانی از خودت انتظار کمتری داشته باشی. یک مکث کوتاه هم خوب است.',
    ),
    (
      Icons.sentiment_very_dissatisfied_rounded,
      'پرفشار',
      'چند نفس آرام بکش. اگر خواستی از کسی که به او اعتماد داری کمک بگیر.',
    ),
    (
      Icons.sentiment_neutral_rounded,
      'معمولی',
      'برای شروع، کاری را انتخاب کن که همین حالا از دستت برمی‌آید.',
    ),
    (
      Icons.sentiment_satisfied_alt_rounded,
      'آرام',
      'اگر دوست داری، این آرامش را با یک مرور کوتاه همراه کن.'
    ),
    (
      Icons.sentiment_very_satisfied_rounded,
      'پرانرژی',
      'می‌توانی انرژی‌ات را برای کاری بگذاری که دوست داری جلو برود.',
    ),
  ];

  late String _key;
  int? _selected;
  int? _saved;
  bool _busy = true;
  bool _unavailable = false;

  @override
  void initState() {
    super.initState();
    _updateDate();
    _load();
  }

  void _updateDate() {
    final day = DateTime.now().toIso8601String().substring(0, 10);
    _key = 'apex360_wellbeing_v1_${widget.scope}_$day';
  }

  Future<void> _load() async {
    try {
      final value = int.tryParse(await _storage.read(key: _key) ?? '');
      if (mounted && value != null && value >= 0 && value < _moods.length) {
        setState(() => _selected = _saved = value);
      }
    } catch (_) {
      if (mounted) setState(() => _unavailable = true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _save(int? value) async {
    if (_busy) return;
    setState(() => _busy = true);
    if (value != null) _updateDate();
    try {
      if (value == null) {
        await _storage.delete(key: _key);
      } else {
        await _storage.write(key: _key, value: value.toString());
      }
      if (!mounted) return;
      setState(() => _saved = _selected = value);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            value == null
                ? 'حال ثبت‌شده پاک شد.'
                : 'حال امروز روی گوشی ثبت شد.',
          ),
        ),
      );
    } catch (_) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('ثبت تغییر ممکن نشد. دوباره تلاش کن.')),
        );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('حال روزانه')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const ApexSection(
            'امروز چه حسی داری؟',
            detail: 'ثبت حال اختیاری است و فقط روی همین گوشی می‌ماند.',
          ),
          if (_busy && _selected == null)
            const LinearProgressIndicator()
          else if (_unavailable)
            const ApexSection('خواندن حال امروز ممکن نشد')
          else ...[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final (index, (face, label, _)) in _moods.indexed)
                  Semantics(
                    label: label,
                    selected: _selected == index,
                    button: true,
                    onTap:
                        _busy ? null : () => setState(() => _selected = index),
                    child: ExcludeSemantics(
                      child: Material(
                        color: _selected == index
                            ? colors.primaryContainer
                            : colors.surfaceContainerLow,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                          side: BorderSide(
                            color: _selected == index
                                ? colors.primary
                                : colors.outlineVariant,
                          ),
                        ),
                        child: InkWell(
                          onTap: _busy
                              ? null
                              : () => setState(() => _selected = index),
                          borderRadius: BorderRadius.circular(20),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              vertical: 10,
                              horizontal: 14,
                            ),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                CircleAvatar(
                                  radius: 19,
                                  backgroundColor: const Color(0xFFFFD875),
                                  foregroundColor: const Color(0xFF533512),
                                  child: Icon(face, size: 30),
                                ),
                                const SizedBox(height: 3),
                                Text(label, style: theme.textTheme.labelLarge),
                                Icon(
                                  _selected == index
                                      ? Icons.check_circle
                                      : Icons.circle_outlined,
                                  size: 16,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            if (_selected case final int index)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 16),
                child: Card(
                  child: ListTile(
                    leading: const Icon(Icons.favorite_border),
                    title: Text(_moods[index].$3),
                  ),
                ),
              ),
            FilledButton.icon(
              onPressed:
                  _busy || _selected == null ? null : () => _save(_selected),
              icon: const Icon(Icons.check_rounded),
              label: Text(
                _saved != null && _saved == _selected
                    ? 'حال امروز ثبت شده'
                    : 'ثبت حال امروز',
              ),
            ),
            if (_saved != null)
              TextButton(
                onPressed: _busy ? null : () => _save(null),
                child: const Text('پاک‌کردن حال ثبت‌شده'),
              ),
          ],
        ],
      ),
    );
  }
}
