"""Fetch a few stock codes from a pywencai query for A12 code pool."""
import sys
sys.path.insert(0, r"F:\v.6\v6-op")
import pywencai

query = "非ST，今日成交额大于近5日平均成交额1.5倍"
print(f"Query: {query}")
try:
    result = pywencai.get(query=query, query_type="stock", perpage=20, page=1)
    if result is not None and hasattr(result, '__len__') and len(result) > 0:
        import pandas as pd
        df = result if isinstance(result, pd.DataFrame) else pd.DataFrame(result)
        print(f"Columns: {list(df.columns)[:10]}")
        # Try to find code column
        code_col = None
        for c in df.columns:
            if "代码" in str(c) or "code" in str(c).lower():
                code_col = c
                break
        if code_col:
            codes = df[code_col].astype(str).str.zfill(6).tolist()[:10]
            print(f"Codes ({len(codes)}): {codes}")
        else:
            print("No code column found, columns:", list(df.columns)[:15])
            print(df.head(3))
    else:
        print("Empty result")
except Exception as e:
    print(f"Error: {e}")
