"""One-time migration: convert candidate_changes.jsonl from V1 to V2 format and deduplicate."""
import json
from pathlib import Path

queue_path = Path(__file__).parent.parent / "canon" / "review_queue" / "candidate_changes.jsonl"
raw_lines = queue_path.read_text(encoding="utf-8").strip().split("\n")
entries = [json.loads(l) for l in raw_lines if l.strip()]

existing: dict[str, dict] = {}
for c in entries:
    qt = c.get("canonical_query_text") or c.get("new_value", "")
    c["canonical_query_text"] = qt
    c.pop("new_value", None)
    c.pop("none_count", None)
    c.pop("error_count", None)
    c.pop("empty_count", None)

    rc = c.pop("result_count", None)
    if rc is not None:
        c.setdefault("result_count_min", rc)
        c.setdefault("result_count_max", rc)
        c.setdefault("result_count_avg", float(rc))

    c.setdefault("success_count", 1 if c.get("success_rate", 0) >= 1.0 else 0)
    c.setdefault("failed_count", 0)
    c.setdefault("updated_at", c.get("created_at", ""))

    key = f"{c.get('skill_key', '')}|{qt}"
    if key not in existing:
        existing[key] = c
    else:
        e = existing[key]
        r1 = e.get("evidence_run_ids", [])
        r2 = c.get("evidence_run_ids", [])
        e["evidence_run_ids"] = list(dict.fromkeys(r1 + r2))
        q1 = e.get("evidence_query_ids", [])
        q2 = c.get("evidence_query_ids", [])
        e["evidence_query_ids"] = list(dict.fromkeys(q1 + q2))
        e["success_count"] = e.get("success_count", 0) + c.get("success_count", 0)
        e["result_count_min"] = min(e.get("result_count_min", 9999), c.get("result_count_min", 9999))
        e["result_count_max"] = max(e.get("result_count_max", 0), c.get("result_count_max", 0))
        total = e["success_count"] + e.get("failed_count", 0)
        e["success_rate"] = round(e["success_count"] / max(total, 1), 3)
        e["result_count_avg"] = round((e["result_count_min"] + e["result_count_max"]) / 2, 1)

print(f"Migrated: {len(entries)} -> {len(existing)} (removed {len(entries)-len(existing)} duplicates)")
for i, (k, v) in enumerate(list(existing.items())[:3]):
    print(f"  {k[:70]}  evidence_run_ids={v['evidence_run_ids']}")

with queue_path.open("w", encoding="utf-8") as f:
    for c in existing.values():
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
print("Done.")
