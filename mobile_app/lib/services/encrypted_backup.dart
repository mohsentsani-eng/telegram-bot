import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

/// Reads and writes the existing Apex360 encrypted backup format.
abstract final class EncryptedBackup {
  static const _format = 'apex360-encrypted-v1';
  static const _maxBytes = 8000000;

  static Future<SecretKey> _key(String password, List<int> salt) => Pbkdf2(
    macAlgorithm: Hmac.sha256(),
    iterations: 600000,
    bits: 256,
  ).deriveKey(secretKey: SecretKey(utf8.encode(password)), nonce: salt);

  static Future<Uint8List> encode(String payload, String password) async {
    final random = Random.secure();
    final salt = List<int>.generate(16, (_) => random.nextInt(256));
    final box = await AesGcm.with256bits().encrypt(
      utf8.encode(payload),
      secretKey: await _key(password, salt),
    );
    final bytes = utf8.encode(jsonEncode({
      'format': _format,
      'salt': base64Encode(salt),
      'nonce': base64Encode(box.nonce),
      'cipher': base64Encode(box.cipherText),
      'mac': base64Encode(box.mac.bytes),
    }));
    if (bytes.length > _maxBytes) throw const FormatException('Backup too large');
    return Uint8List.fromList(bytes);
  }

  static Future<String> decode(Uint8List bytes, String password) async {
    if (bytes.length > _maxBytes) throw const FormatException('Backup too large');
    final envelope = jsonDecode(utf8.decode(bytes));
    if (envelope is! Map<String, dynamic> || envelope['format'] != _format) {
      throw const FormatException('Invalid backup envelope');
    }
    List<int> field(String name) {
      final value = envelope[name];
      if (value is! String) throw const FormatException('Missing backup field');
      return base64Decode(value);
    }
    final salt = field('salt');
    final nonce = field('nonce');
    final mac = field('mac');
    final cipher = field('cipher');
    if (salt.length != 16 || nonce.length != 12 || mac.length != 16 || cipher.isEmpty) {
      throw const FormatException('Invalid backup fields');
    }
    final payload = await AesGcm.with256bits().decrypt(
      SecretBox(cipher, nonce: nonce, mac: Mac(mac)),
      secretKey: await _key(password, salt),
    );
    return utf8.decode(payload);
  }
}
