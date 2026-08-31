import sys, os
sys.path.insert(0, os.getcwd())
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
res = client.get("/api/v1/user-squad/season-history")
print("Status Code:", res.status_code)
data = res.json()
print("Summary Metrics:", data["summary_metrics"])
print("Chips Status:", data["chips_status"])
print("History Rows count:", len(data["history_rows"]))
if data["history_rows"]:
    print("GW1 Row:", data["history_rows"][0])
