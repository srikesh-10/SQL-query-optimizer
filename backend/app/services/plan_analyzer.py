"""
Execution Plan Parser and Rule-Based Analyzer.
Extracts structured metrics, scan nodes, join nodes, and evidence-based findings
from raw PostgreSQL JSON plans.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class PlanSummary(BaseModel):
    root_node_type: str
    total_cost: float
    startup_cost: float
    plan_rows: int
    plan_width: int
    planning_time_ms: Optional[float] = None
    node_count: int


class ScanNode(BaseModel):
    node_type: str
    relation_name: Optional[str] = None
    alias: Optional[str] = None
    index_name: Optional[str] = None
    filter_condition: Optional[str] = None
    index_condition: Optional[str] = None
    total_cost: float
    plan_rows: int


class JoinNode(BaseModel):
    node_type: str
    join_type: Optional[str] = None
    join_filter: Optional[str] = None
    hash_condition: Optional[str] = None
    total_cost: float
    plan_rows: int


class Finding(BaseModel):
    code: str
    title: str
    severity: str  # 'info', 'warning', 'high'
    evidence: str
    explanation: str
    recommendation: Optional[str] = None


class AnalysisResult(BaseModel):
    status: str
    validated_sql: str
    plan_summary: PlanSummary
    scan_nodes: List[ScanNode]
    join_nodes: List[JoinNode]
    findings: List[Finding]
    metadata: Dict[str, Any]


# Configurable heuristics thresholds
HIGH_COST_THRESHOLD = 5000.0
HIGH_ROWS_THRESHOLD = 10000


def analyze_plan(raw_plan_dict: Dict[str, Any], validated_sql: str) -> AnalysisResult:
    """
    Parses PostgreSQL raw JSON plan into structured summary, nodes, and rule-based findings.
    """
    root_plan = raw_plan_dict.get("Plan", {})
    planning_time = raw_plan_dict.get("Planning Time")

    # Traverse AST/plan tree to gather all nodes
    all_nodes: List[Dict[str, Any]] = []
    scan_nodes: List[ScanNode] = []
    join_nodes: List[JoinNode] = []

    def traverse(node: Dict[str, Any]):
        if not node or not isinstance(node, dict):
            return
        all_nodes.append(node)

        node_type = str(node.get("Node Type", "Unknown"))
        total_cost = float(node.get("Total Cost", 0.0))
        plan_rows = int(node.get("Plan Rows", 0))

        # Check for Scan nodes
        if "Scan" in node_type:
            scan_nodes.append(ScanNode(
                node_type=node_type,
                relation_name=node.get("Relation Name"),
                alias=node.get("Alias"),
                index_name=node.get("Index Name"),
                filter_condition=node.get("Filter"),
                index_condition=node.get("Index Cond"),
                total_cost=total_cost,
                plan_rows=plan_rows,
            ))

        # Check for Join nodes
        if "Join" in node_type or "Nested Loop" in node_type or "Merge" in node_type:
            join_nodes.append(JoinNode(
                node_type=node_type,
                join_type=node.get("Join Type"),
                join_filter=node.get("Join Filter"),
                hash_condition=node.get("Hash Cond"),
                total_cost=total_cost,
                plan_rows=plan_rows,
            ))

        # Recurse children
        for child in node.get("Plans", []):
            traverse(child)

    traverse(root_plan)

    # Build PlanSummary
    summary = PlanSummary(
        root_node_type=root_plan.get("Node Type", "Unknown"),
        total_cost=float(root_plan.get("Total Cost", 0.0)),
        startup_cost=float(root_plan.get("Startup Cost", 0.0)),
        plan_rows=int(root_plan.get("Plan Rows", 0)),
        plan_width=int(root_plan.get("Plan Width", 0)),
        planning_time_ms=float(planning_time) if planning_time is not None else None,
        node_count=len(all_nodes),
    )

    # Generate rule-based findings
    findings: List[Finding] = []

    # Finding 1: Sequential scans detected
    seq_scans = [s for s in scan_nodes if s.node_type == "Seq Scan"]
    for s in seq_scans:
        rel = s.relation_name or "table"
        if s.plan_rows > HIGH_ROWS_THRESHOLD or s.total_cost > 500:
            findings.append(Finding(
                code="PERF_SEQ_SCAN_LARGE_TABLE",
                title=f"Sequential Scan on Table '{rel}'",
                severity="warning",
                evidence=f"Table '{rel}' is scanned sequentially (cost: {s.total_cost:.1f}, rows: {s.plan_rows:,}). Filter: {s.filter_condition or 'None'}.",
                explanation=f"PostgreSQL planner chose a Sequential Scan across all pages of '{rel}'. On large tables, this requires reading many data blocks from disk/memory.",
                recommendation=f"Examine filters on '{rel}' to see if creating a selective B-Tree index could replace the full table scan with an Index Scan."
            ))
        else:
            findings.append(Finding(
                code="PERF_SEQ_SCAN_SMALL_TABLE",
                title=f"Sequential Scan on Table '{rel}'",
                severity="info",
                evidence=f"Table '{rel}' scanned sequentially (cost: {s.total_cost:.1f}, rows: {s.plan_rows:,}).",
                explanation=f"A sequential scan was selected for '{rel}'. For smaller tables or low cost estimates, sequential scan is often faster than index lookups due to sequential page reading.",
                recommendation=None
            ))

    # Finding 2: Index Scans utilized
    index_scans = [s for s in scan_nodes if "Index" in s.node_type]
    for idx_scan in index_scans:
        findings.append(Finding(
            code="PERF_INDEX_SCAN_USED",
            title=f"Index Utilized: '{idx_scan.index_name}'",
            severity="info",
            evidence=f"Used {idx_scan.node_type} with index '{idx_scan.index_name}' on relation '{idx_scan.relation_name}' (cost: {idx_scan.total_cost:.1f}).",
            explanation=f"PostgreSQL leveraged index '{idx_scan.index_name}' to directly look up matching rows instead of scanning the whole table.",
            recommendation=None
        ))

    # Finding 3: Join strategy assessment
    for join in join_nodes:
        if join.node_type == "Nested Loop" and join.total_cost > HIGH_COST_THRESHOLD:
            findings.append(Finding(
                code="PERF_EXPENSIVE_NESTED_LOOP",
                title="High Cost Nested Loop Join",
                severity="warning",
                evidence=f"Nested Loop Join cost estimated at {join.total_cost:.1f} for {join.plan_rows:,} rows.",
                explanation="Nested loop joins run an inner scan for each row from the outer relation. When row counts are large, this can be computationally expensive.",
                recommendation="Verify join conditions have matching indexes on the inner table to keep inner lookups fast."
            ))
        elif join.node_type == "Hash Join":
            findings.append(Finding(
                code="PERF_HASH_JOIN_USED",
                title="Hash Join Strategy Selected",
                severity="info",
                evidence=f"Hash Join on condition: {join.hash_condition or 'N/A'} (cost: {join.total_cost:.1f}).",
                explanation="Hash Join creates an in-memory hash table of the smaller relation before scanning the larger relation. This is typically efficient for unsorted, equi-join queries.",
                recommendation=None
            ))

    # Finding 4: High overall query cost
    if summary.total_cost >= HIGH_COST_THRESHOLD:
        findings.append(Finding(
            code="PERF_HIGH_ESTIMATED_COST",
            title="High Total Estimated Query Cost",
            severity="warning",
            evidence=f"Total cost is {summary.total_cost:.1f} (threshold: {HIGH_COST_THRESHOLD:.1f}).",
            explanation="The PostgreSQL optimizer estimated a high overall cost to execute this plan.",
            recommendation="Review the scan and join operations in the query plan to see where the majority of the cost is accumulated."
        ))

    # Construct metadata
    metadata = {
        "engine": "PostgreSQL",
        "plan_type": "EXPLAIN (FORMAT JSON, COSTS TRUE)",
        "is_runtime_benchmark": False,
        "note": "Values are planner estimates based on table statistics, not actual execution runtimes.",
    }

    return AnalysisResult(
        status="success",
        validated_sql=validated_sql,
        plan_summary=summary,
        scan_nodes=scan_nodes,
        join_nodes=join_nodes,
        findings=findings,
        metadata=metadata,
    )
