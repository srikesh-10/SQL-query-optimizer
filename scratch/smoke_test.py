import os
import sys

# Ensure backend directory is in Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=== 1. Health & Database Readiness ===")
res_health = client.get("/health/ready")
print("Readiness status code:", res_health.status_code)
print("Readiness body:", res_health.json())
assert res_health.status_code == 200

print("\n=== 2. Static Plan Analysis ===")
orig_sql = "SELECT * FROM users WHERE first_name = 'Emily';"
res_analyze = client.post("/api/v1/analyze", json={"sql": orig_sql})
print("Analyze status code:", res_analyze.status_code)
analyze_data = res_analyze.json()
print("Root node:", analyze_data["plan_summary"]["root_node_type"])
print("Total cost:", analyze_data["plan_summary"]["total_cost"])
print("Rewrite candidates found:", len(analyze_data.get("rewrite_candidates", [])))
cand_sql = analyze_data["rewrite_candidates"][0]["rewritten_sql"]
print("Candidate SQL:", cand_sql)

print("\n=== 3. Safe Result Equivalence Comparison ===")
res_equiv = client.post("/api/v1/validation/compare-results", json={
    "original_sql": orig_sql,
    "candidate_sql": cand_sql,
    "confirmed": True,
    "row_limit": 1000,
})
print("Validation status code:", res_equiv.status_code)
equiv_data = res_equiv.json()
print("Equivalence status:", equiv_data["status"])
print("Matched:", equiv_data["matched"])
print("Is complete:", equiv_data["is_complete_comparison"])
assert equiv_data["status"] == "equivalent"

print("\n=== 4. Safe Query Benchmarking ===")
res_bench = client.post("/api/v1/benchmarks", json={
    "sql": orig_sql,
    "repetitions": 3,
})
print("Benchmark status code:", res_bench.status_code)
bench_data = res_bench.json()
print("Benchmark status:", bench_data["status"])
print("Median exec time ms:", bench_data["median_execution_time_ms"])
print("Total cost:", bench_data["estimated_total_cost"])

print("\n=== 5. Unified Optimizer Evaluation (Validated Case) ===")
res_eval_valid = client.post("/api/v1/evaluations", json={
    "original_sql": orig_sql,
    "candidate_sql": cand_sql,
    "confirmed": True,
    "repetitions": 3,
})
print("Evaluation valid status code:", res_eval_valid.status_code)
eval_valid_data = res_eval_valid.json()
print("Evaluation ID:", eval_valid_data["id"])
print("Correctness status:", eval_valid_data["correctness_status"])
print("Original median ms:", eval_valid_data["original_median_execution_time_ms"])
print("Candidate median ms:", eval_valid_data["candidate_median_execution_time_ms"])
print("Performance assessment:", eval_valid_data["performance_assessment"])
print("Recommendation:", eval_valid_data["recommendation"])
print("Rationale:", eval_valid_data["recommendation_rationale"])
eval_id = eval_valid_data["id"]

print("\n=== 6. Unified Optimizer Evaluation (Diverging/Different Case) ===")
diff_sql = "SELECT id, email, first_name FROM users WHERE first_name = 'Bob';"
res_eval_diff = client.post("/api/v1/evaluations", json={
    "original_sql": orig_sql,
    "candidate_sql": diff_sql,
    "confirmed": True,
    "repetitions": 3,
})
print("Evaluation diff status code:", res_eval_diff.status_code)
eval_diff_data = res_eval_diff.json()
print("Correctness status:", eval_diff_data["correctness_status"])
print("Original runs executed:", len(eval_diff_data["original_runs"]))
print("Candidate runs executed:", len(eval_diff_data["candidate_runs"]))
print("Recommendation:", eval_diff_data["recommendation"])
print("Performance assessment:", eval_diff_data["performance_assessment"])
assert eval_diff_data["correctness_status"] == "different"
assert eval_diff_data["recommendation"] == "do_not_recommend"
assert len(eval_diff_data["original_runs"]) == 0
assert len(eval_diff_data["candidate_runs"]) == 0

print("\n=== 7. Evaluation History Retrieval ===")
res_hist = client.get("/api/v1/evaluations?limit=10&offset=0")
print("History status code:", res_hist.status_code)
hist_data = res_hist.json()
print("Total evaluations in database:", hist_data["total"])
print("Returned items count:", len(hist_data["items"]))

print("\n=== 8. Individual Evaluation Retrieval By ID ===")
res_single = client.get(f"/api/v1/evaluations/{eval_id}")
print("Single eval status code:", res_single.status_code)
single_data = res_single.json()
print("Retrieved ID:", single_data["id"])
print("Original runs count:", len(single_data["original_runs"]))
print("Candidate runs count:", len(single_data["candidate_runs"]))

print("\n=== ALL 8 END-TO-END WORKFLOW CHECKS PASSED CLEANLY! ===")
