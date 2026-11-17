"""October: add transaction files to September's, replace master files (OCTOBER.md)."""
import sys, os, pandas as pd
sep, octo, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
TX = ["delivery_log.csv", "invoices.csv", "purchase_orders.csv", "supplier_bills.csv", "inbox.csv"]
MASTER = ["customers.csv", "contract_prices.csv", "products.csv", "suppliers.csv"]
for f in TX:
    a = pd.read_csv(os.path.join(sep, f), dtype=str, keep_default_na=False)
    b = pd.read_csv(os.path.join(octo, f), dtype=str, keep_default_na=False) if os.path.exists(os.path.join(octo, f)) else a.iloc[0:0]
    m = pd.concat([a, b]).drop_duplicates()
    m.to_csv(os.path.join(out, f), index=False); print(f, len(a), "+", len(b), "=", len(m))
for f in MASTER:
    src = os.path.join(octo, f) if os.path.exists(os.path.join(octo, f)) else os.path.join(sep, f)
    pd.read_csv(src, dtype=str, keep_default_na=False).to_csv(os.path.join(out, f), index=False); print(f, "from", src)
