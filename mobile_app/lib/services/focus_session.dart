import 'dart:convert';

class FocusSession {
  const FocusSession({required this.total, required this.paused, this.endsAt});

  factory FocusSession.start(int minutes, DateTime now) => FocusSession(
    total: minutes * 60,
    paused: minutes * 60,
    endsAt: now.add(Duration(minutes: minutes)),
  );

  factory FocusSession.decode(String raw) {
    final data = jsonDecode(raw) as Map<String, dynamic>;
    final total = data['total'] as int;
    final paused = data['paused'] as int;
    if (total <= 0 || paused < 0 || paused > total) {
      throw const FormatException('Invalid focus session');
    }
    return FocusSession(
      total: total,
      paused: paused,
      endsAt: data['endsAt'] == null
          ? null
          : DateTime.fromMillisecondsSinceEpoch(
              data['endsAt'] as int,
              isUtc: true,
            ),
    );
  }

  final int total;
  final int paused;
  final DateTime? endsAt;

  int remaining(DateTime now) {
    final deadline = endsAt;
    if (deadline == null) return paused;
    return ((deadline.difference(now).inMilliseconds + 999) ~/ 1000)
        .clamp(0, total)
        .toInt();
  }

  int elapsedMinutes(DateTime now) => (total - remaining(now)) ~/ 60;

  FocusSession pause(DateTime now) =>
      FocusSession(total: total, paused: remaining(now));

  FocusSession resume(DateTime now) => FocusSession(
    total: total,
    paused: paused,
    endsAt: now.add(Duration(seconds: paused)),
  );

  String encode() => jsonEncode({
    'total': total,
    'paused': paused,
    'endsAt': endsAt?.millisecondsSinceEpoch,
  });
}
