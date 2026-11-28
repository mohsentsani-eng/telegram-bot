"""Check the public Apex360 contract on an approved HTTPS test origin."""
import argparse
import re
import ssl
from urllib.parse import urlsplit

import httpx


def check_origin(origin: str, *, bot: str = "TaranomHamDeliBot",
                 ca_file: str | None = None) -> None:
    if not re.fullmatch(r"[a-zA-Z0-9_]{2,29}[bB][oO][tT]", bot):
        raise ValueError("Expected a Telegram bot username without @")
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.path not in ("", "/") or "?" in origin or "#" in origin):
        raise ValueError("Supply an approved HTTPS origin without credentials, path, query or fragment")
    tls = ssl.create_default_context(cafile=ca_file)
    with httpx.Client(base_url=origin, verify=tls, trust_env=False,
                      follow_redirects=False, timeout=8) as client:
        for path in ("/api/v1/mobile/health", "/api/v1/mobile/capabilities",
                     "/admin/login", "/counselor/login"):
            response = client.get(path)
            if response.status_code != 200:
                raise ValueError(f"{path}: expected HTTP 200, got {response.status_code}")
            if response.headers.get("cache-control") != "no-store":
                raise ValueError(f"{path}: missing private-response cache policy")
            if path.endswith("/health"):
                data = response.json()
                if data.get("service") != "taranom-mobile-api" or data.get("ok") is not True:
                    raise ValueError(f"{path}: unexpected API identity")
            elif path.endswith("/capabilities"):
                data = response.json()
                if (data.get("api_version") != 1 or data.get("student_workflow_version") != 17
                        or data.get("authentication") != "telegram-deep-link-approval"
                        or not all(data.get(key) is True for key in
                                   ("counselor_assignment", "plan_receipts", "report_feedback"))):
                    raise ValueError(f"{path}: incompatible student workflow")
                if data.get("telegram_bot_username", "TaranomHamDeliBot") != bot:
                    raise ValueError(f"{path}: Telegram bot differs from the expected build configuration")
            elif "text/html" not in response.headers.get("content-type", ""):
                raise ValueError(f"{path}: expected an HTML login page")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin")
    parser.add_argument("--bot", default="TaranomHamDeliBot")
    parser.add_argument("--ca-file", help="Trust root for an isolated HTTPS rehearsal")
    args = parser.parse_args()
    try:
        check_origin(args.origin, bot=args.bot, ca_file=args.ca_file)
    except (ValueError, OSError, httpx.HTTPError) as error:
        parser.exit(1, f"Apex360 HTTPS check failed: {error}\n")
    print("Apex360 HTTPS contract and both panel login pages verified.")


if __name__ == "__main__":
    main()
