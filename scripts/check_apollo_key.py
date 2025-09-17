#!/usr/bin/env python3
"""Quick Apollo API key health check.

Performs a lightweight /people/search request with harmless params to verify:
  - Key present
  - HTTP 200 from Apollo
  - Basic shape of response (JSON with 'people')
No email unlock or credits-consuming deep actions are attempted.

Exit codes:
  0 = healthy
  1 = missing key
  2 = HTTP error / unauthorized / bad response
  3 = unexpected exception
"""
from __future__ import annotations
import os, sys, json, time
import requests

APOLLO_BASE = "https://api.apollo.io/api/v1"
API_KEY = os.getenv("APOLLO_API_KEY", "").strip()

def main():
    if not API_KEY:
        print("STATUS: MISSING_KEY")
        return 1
    headers = {"Content-Type": "application/json", "X-Api-Key": API_KEY}
    params = {
        # Very broad, small page; should succeed quickly without exhausting credits
        "page": 1,
        "per_page": 1,
        "person_locations[]": "United States",
    }
    url = f"{APOLLO_BASE}/people/search"
    t0 = time.time()
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
    except Exception as e:
        print(f"STATUS: NETWORK_ERROR detail={e}")
        return 2
    latency = (time.time() - t0) * 1000
    masked = API_KEY[:4] + "***" + API_KEY[-4:] if len(API_KEY) >= 8 else "***"
    if r.status_code == 401:
        print(f"STATUS: UNAUTHORIZED code=401 key={masked}")
        return 2
    if r.status_code == 403:
        print(f"STATUS: FORBIDDEN code=403 key={masked}")
        return 2
    if r.status_code >= 500:
        print(f"STATUS: APOOL_SERVER_ERROR code={r.status_code}")
        return 2
    if r.status_code != 200:
        snippet = r.text[:160].replace('\n',' ')
        print(f"STATUS: BAD_STATUS code={r.status_code} key={masked} body='{snippet}'")
        return 2
    try:
        data = r.json()
    except Exception:
        print("STATUS: INVALID_JSON")
        return 2
    people = data.get("people")
    if people is None:
        print("STATUS: MALFORMED_RESPONSE missing_people_key")
        return 2
    # success
    print(json.dumps({
        "status": "OK",
        "key_masked": masked,
        "latency_ms": round(latency,2),
        "people_sample_count": len(people),
    }))
    return 0

if __name__ == "__main__":
    try:
        code = main()
        sys.exit(code)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"STATUS: EXCEPTION detail={e}")
        sys.exit(3)
