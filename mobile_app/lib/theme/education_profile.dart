import 'apex_components.dart';

bool isNinthGrade(String grade) {
  final value = latinDigits(grade).trim().replaceFirst(RegExp(r'^پایه\s*'), '');
  return value == 'نهم' || value == '9' || value == 'نهم متوسطه';
}
