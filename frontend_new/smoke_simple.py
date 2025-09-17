import urllib.request, json, time

run_payload = json.dumps({"query":"python developer"}).encode()
req = urllib.request.Request("http://127.0.0.1:8011/api/jobs/run", data=run_payload, headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req) as r:
    run_data = json.loads(r.read().decode())
print("Run:", run_data)
run_id = run_data[task_id]
for _ in range(8):
    time.sleep(1)
    with urllib.request.urlopen(f"http://127.0.0.1:8011/api/runs/{run_id}/jobs") as r:
        jobs = json.loads(r.read().decode())
    if jobs:
        break
print(Jobs
