import json, time, urllib.request

def post_json(url, data):
    data_bytes = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data_bytes, headers={Content-Type:application/json})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()

def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode()

run_raw = post_json("http://127.0.0.1:8011/api/jobs/run", {"query":"python developer"})
print("Run raw", run_raw[:160])
run_id = json.loads(run_raw)["task_id"]
print("Run ID", run_id)
# wait briefly for pipeline
for i in range(6):
    time.sleep(1)
jobs_raw = get(f"http://127.0.0.1:8011/api/runs/{run_id}/jobs")
print("Jobs raw", jobs_raw[:200])
jobs = json.loads(jobs_raw)
if not jobs:
    print("No jobs returned")
    raise SystemExit
jid = jobs[0].get("id") or jobs[0].get("job_id")
print("First job id", jid)
# details
detail_raw = get(f"http://127.0.0.1:8011/api/runs/{run_id}/jobs/{jid}/details")
print("Detail raw", detail_raw[:300])
detail = json.loads(detail_raw)
print("Contacts count", len(detail.get("recruiter_contacts") or []))
