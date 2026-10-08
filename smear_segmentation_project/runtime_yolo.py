"""Start the standalone macOS YOLO runtime (one model, one worker)."""
from __future__ import annotations

import argparse
import ipaddress
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("YOLO_RUNTIME_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("YOLO_RUNTIME_PORT", "8765")))
    args = parser.parse_args()
    address = ipaddress.ip_address(args.host)
    if address.is_unspecified or not (address.is_loopback or address.is_private):
        parser.error("Bind to an explicit loopback/private interface; wildcard/public binds are forbidden")
    if not 1 <= args.port <= 65535:
        parser.error("Port must be in 1..65535")
    uvicorn.run("smear_segmentation.runtime_api:create_app", factory=True, host=args.host,
                port=args.port, workers=1, access_log=False, limit_concurrency=4,
                timeout_keep_alive=5)


if __name__ == "__main__":
    main()
