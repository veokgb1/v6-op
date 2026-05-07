"""Use the adapter directly to fetch codes for A12 code pool."""
import sys
from pathlib import Path

PROJECT = Path(r"F:\v.6\v6-op")
sys.path.insert(0, str(PROJECT / "query_lab" / "scripts"))

from adapters.wencai_astock_adapter import WencaiAstockAdapter

adapter = WencaiAstockAdapter(PROJECT, dry_run=False)

# Use A11-005 query (非ST, 成交额>近5日均×1.5) - returned rc=21
result = adapter.query("非ST，今日成交额大于近5日平均成交额1.5倍", limit=10)
print(f"status={result['status']} rc={result['result_count']} elapsed={result['elapsed_ms']}ms")
codes = result.get("codes", [])
print(f"codes: {codes}")
