"""Allow loopback traffic for the generated Android debug source set."""
from pathlib import Path
from xml.etree import ElementTree as ET

debug = Path("android/app/src/debug")
manifest = debug / "AndroidManifest.xml"
namespace = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", namespace)
tree = ET.parse(manifest)
root = tree.getroot()
application = root.find("application")
if application is None:
    application = ET.SubElement(root, "application")
policy = "@xml/apex_loopback_network_policy"
application.set(f"{{{namespace}}}networkSecurityConfig", policy)
ET.SubElement(application, "meta-data", {
    f"{{{namespace}}}name": "io.flutter.network-policy",
    f"{{{namespace}}}resource": policy,
})
tree.write(manifest, encoding="unicode")
xml = debug / "res" / "xml"
xml.mkdir(parents=True, exist_ok=True)
(xml / "apex_loopback_network_policy.xml").write_text("""<network-security-config>
    <base-config cleartextTrafficPermitted="false" />
    <domain-config cleartextTrafficPermitted="true">
        <domain>127.0.0.1</domain>
    </domain-config>
</network-security-config>
""")
