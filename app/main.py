import asyncio
import os
import socket

from dotenv import load_dotenv

load_dotenv()

from .db import init_db
from .admin import app
from .bot import run_bot


def _find_available_port(host: str, preferred: int, attempts: int = 20) -> int:
    """Return preferred port if free; otherwise find the next available port."""
    for port in range(preferred, preferred + attempts):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return port
        except OSError:
            continue
        finally:
            sock.close()
    raise RuntimeError(
        f"Could not find an available admin port in range {preferred}-{preferred + attempts - 1}"
    )


async def main():
    import uvicorn

    init_db()

    host = os.getenv("ADMIN_HOST", "0.0.0.0").strip() or "0.0.0.0"
    try:
        preferred_port = int(os.getenv("PORT", os.getenv("ADMIN_PORT", "8000")))
    except ValueError:
        preferred_port = 8000

    port = _find_available_port(host, preferred_port)

    if port != preferred_port:
        print(
            f"[WEB] Port {preferred_port} is already in use. "
            f"Starting admin panel on http://{host}:{port}",
            flush=True,
        )
    else:
        print(f"[WEB] Admin panel: http://{host}:{port}", flush=True)

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    await asyncio.gather(
        server.serve(),
        run_bot(),
    )


if __name__ == "__main__":
    asyncio.run(main())
