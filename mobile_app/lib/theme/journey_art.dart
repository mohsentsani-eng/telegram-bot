import 'package:flutter/material.dart';

class TaranomBrand extends StatelessWidget {
  const TaranomBrand({super.key, this.light = false});
  final bool light;

  @override
  Widget build(BuildContext context) {
    final color = light
        ? const Color(0xFFD5E6FF)
        : Theme.of(context).colorScheme.primary;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.waves_rounded, color: color, size: 24),
        const SizedBox(width: 7),
        Flexible(
          child: Text(
            'ترنم همدلی',
            style: Theme.of(context).textTheme.titleMedium
                ?.copyWith(color: color),
          ),
        ),
      ],
    );
  }
}

class NightLandscape extends CustomPainter {
  const NightLandscape();

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 360, size.height / 240);
    final paint = Paint()..color = const Color(0xFF203F77);
    canvas.drawCircle(const Offset(72, 75), 49, paint);
    paint.color = const Color(0xFF2F5288);
    canvas.drawCircle(const Offset(78, 71), 28, paint);
    paint.color = const Color(0xFF203761);
    canvas.drawPath(
      Path()
        ..moveTo(0, 169)
        ..quadraticBezierTo(55, 114, 126, 154)
        ..quadraticBezierTo(220, 201, 360, 112)
        ..lineTo(360, 240)
        ..lineTo(0, 240)
        ..close(),
      paint,
    );
    paint.color = const Color(0xFF172D53);
    canvas.drawPath(
      Path()
        ..moveTo(0, 199)
        ..quadraticBezierTo(120, 158, 194, 210)
        ..quadraticBezierTo(275, 223, 360, 177)
        ..lineTo(360, 240)
        ..lineTo(0, 240)
        ..close(),
      paint,
    );
    paint.color = const Color(0xFFC4D9FA);
    for (final (x, y, radius) in [
      (26.0, 44.0, 1.7),
      (124.0, 25.0, 2.2),
      (137.0, 86.0, 1.4),
      (172.0, 20.0, 1.2),
      (309.0, 19.0, 1.2),
      (19.0, 108.0, 1.4),
    ]) {
      canvas.drawCircle(Offset(x, y), radius, paint);
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(NightLandscape oldDelegate) => false;
}

class TrailPainter extends CustomPainter {
  const TrailPainter(this.color, this.rtl);
  final Color color;
  final bool rtl;

  @override
  void paint(Canvas canvas, Size size) {
    final x = rtl ? size.width - 26 : 26.0;
    final paint = Paint()
      ..color = color
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    for (double y = 25; y < size.height - 25; y += 9) {
      final wave = ((y ~/ 9) % 14 - 7).abs().toDouble() * .55;
      canvas.drawLine(Offset(x - wave, y), Offset(x - wave, y + 2), paint);
    }
  }

  @override
  bool shouldRepaint(TrailPainter oldDelegate) =>
      color != oldDelegate.color || rtl != oldDelegate.rtl;
}
