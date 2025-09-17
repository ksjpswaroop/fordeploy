"""Quick endpoint reachability checker.

Loads the FastAPI app (app.main:app) and attempts requests against
all GET/HEAD routes that do not require path parameters. Uses the
development auth bypass token if configured (DEV_BEARER_TOKEN).

Exit code 0 if all tested routes returned a non-error (status < 500).
Prints a summary table.
"""

from fastapi.testclient import TestClient
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Ensure project root on sys.path when executed as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEV_BEARER_TOKEN", os.getenv("DEV_BEARER_TOKEN", "dev-123"))

from app.main import app  # noqa: E402

client = TestClient(app)

DEV_TOKEN = os.getenv("DEV_BEARER_TOKEN")
AUTH_HEADERS = {"Authorization": f"Bearer {DEV_TOKEN}"} if DEV_TOKEN else {}


def is_plain_route(path: str) -> bool:
    """Return True if route path has no path params."""
    return "{" not in path and "}" not in path


def main() -> int:
    tested: List[Tuple[str, str, int]] = []
    failures: List[Tuple[str, str, int]] = []
    for route in app.routes:
        methods = getattr(route, "methods", set())
        path = getattr(route, "path", "")
        if not methods or not path:
            continue
        if not is_plain_route(path):
            continue  # skip dynamic paths
        for method in sorted(m for m in methods if m in {"GET", "HEAD"}):
            try:
                resp = client.request(method, path, headers=AUTH_HEADERS)
                code = resp.status_code
                tested.append((method, path, code))
                if code >= 500:
                    failures.append((method, path, code))
            except Exception:
                failures.append((method, path, 0))
    # Output
    width = 6
    print("METHOD  CODE  PATH")
    for method, path, code in tested:
        print(f"{method:<6} {code:<4}  {path}")
    print()
    print(f"Tested {len(tested)} routes. Failures: {len(failures)}")
    if failures:
        print("Failures (>=500 or exception):")
        for method, path, code in failures:
            print(f"  {method} {path} -> {code}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
