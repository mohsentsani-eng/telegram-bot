import 'package:flutter/material.dart';

String fa(Object? value) => value.toString().replaceAllMapped(
  RegExp('[0-9]'),
  (digit) => '۰۱۲۳۴۵۶۷۸۹'[int.parse(digit[0]!)],
);

String latinDigits(String input) =>
    input.replaceAllMapped(RegExp(r'[۰-۹٠-٩]'), (m) {
      final digit = m[0]!.codeUnitAt(0);
      return (digit >= 0x06f0 ? digit - 0x06f0 : digit - 0x0660).toString();
    });

class ApexSection extends StatelessWidget {
  const ApexSection(this.title, {super.key, this.detail});
  final String title;
  final String? detail;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 12, bottom: 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        if (detail != null) Text(detail!),
      ],
    ),
  );
}

class SubjectMark extends StatelessWidget {
  const SubjectMark(this.subject, {super.key});
  final String subject;

  @override
  Widget build(BuildContext context) {
    final c = Theme.of(context).colorScheme;
    final (bg, fg, icon) = switch (subject.runes.fold(0, (a, b) => a + b) % 3) {
      0 => (c.primaryContainer, c.onPrimaryContainer, Icons.book_rounded),
      1 => (c.secondaryContainer, c.onSecondaryContainer, Icons.school_rounded),
      _ => (c.tertiaryContainer, c.onTertiaryContainer, Icons.layers_rounded),
    };
    return ExcludeSemantics(
      child: Container(
        width: 46,
        height: 46,
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Icon(icon, color: fg),
      ),
    );
  }
}

class MinuteChoices extends StatelessWidget {
  const MinuteChoices({super.key, required this.onSelect, this.selected});
  final ValueChanged<int> onSelect;
  final int? selected;

  @override
  Widget build(BuildContext context) => Wrap(
    spacing: 8,
    children: [
      for (final value in [15, 25, 45, 60])
        ChoiceChip(
          label: Text('${fa(value)} دقیقه'),
          selected: selected == value,
          onSelected: (_) => onSelect(value),
        ),
    ],
  );
}
