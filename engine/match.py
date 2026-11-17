"""Three-way match per PO: PO amount vs value accepted at the dock vs everything billed against it, across all bills.
Billed must be <= PO amount and <= accepted value. Item lines only; freight is checked separately by rule 7.
These rows are a control view (evidence section 'match'); the money itself is already in findings.csv
as OVERPO / OVERQTYAP / DUPBILL rows, so nothing is counted twice."""
import re
from common import *

def norm_po(s):
    m = re.search(r"(\d{5})", s or "")
    return f"PO-{m.group(1)}" if m else ""

def rows(g, findings):
    sb, po = g["sb"].copy(), g["po"].copy()
    import ap
    # reuse the AP matcher's repaired PO refs
    sb["pon"] = sb.po_ref.map(norm_po)
    codes = po.groupby("po_no").supplier_item_code.apply(set).to_dict()
    sup_of = po.groupby("po_no").supplier_id.first().to_dict()
    from collections import defaultdict
    by_code = defaultdict(list)
    for p, cs in codes.items():
        for c in cs:
            by_code[(sup_of[p], c)].append(p)
    S = g["su"].set_index("quickbooks_vendor_name").supplier_id.to_dict()
    for bid, grp in sb.groupby("bill_id"):
        p = grp.iloc[0].pon
        items = set(grp[grp.line_type == "ITEM"].supplier_item_code)
        if p in codes and items <= codes[p]:
            continue
        cand = defaultdict(int)
        for c in items:
            for q in by_code.get((S[grp.iloc[0].vendor], c), []):
                cand[q] += 1
        if cand:
            sb.loc[sb.bill_id == bid, "pon"] = max(cand, key=cand.get)
    dup = {f["bill_id"] for f in findings if f["kind"] == "DUPBILL"}
    lines = po.drop_duplicates(["po_no", "po_line"])
    pov = lines.assign(v=lines.line_amount.astype(float)).groupby("po_no").v.sum()
    acc = po.assign(v=po.qty_accepted.replace("", "0").astype(float) * po.unit_cost.astype(float)).groupby("po_no").v.sum()
    it = sb[sb.line_type == "ITEM"]
    billed = it.assign(v=it.amount.astype(float)).groupby("pon").v.sum()
    billed_ex_dup = it[~it.bill_id.isin(dup)].assign(v=lambda d: d.amount.astype(float)).groupby("pon").v.sum()
    nbills = sb.groupby("pon").bill_id.apply(lambda s: sorted(set(s))).to_dict()
    hdr = po.groupby("po_no").agg(sup=("supplier_name", "first"), date=("po_date", "first"), buyer=("buyer", "first"), total=("po_total", "first"))
    out = []
    for p, h in hdr.iterrows():
        b = round(billed.get(p, 0.0), 2); bx = round(billed_ex_dup.get(p, 0.0), 2)
        pv = round(pov.get(p, 0.0), 2); av = round(acc.get(p, 0.0), 2)
        bills = nbills.get(p, [])
        if b > pv + 0.01:
            st = "Over PO"
        elif b > av + 0.01:
            st = "Over receipt"
        elif b == 0:
            st = "Not billed"
        elif b < av - 0.01:
            st = "Partly billed"
        else:
            st = "Matched"
        out.append(dict(finding_id=f"MATCH-{p}", file=st, record=p, shows=h.sup, expected="", section="match", txn_ref=p,
                        doc_type="Three-way match", doc_no=p, line_no=str(len(bills)), item=", ".join(bills), description=f"PO {h.date}, buyer {h.buyer}",
                        qty=f"{pv:.2f}", unit=f"{av:.2f}", unit_price=f"{b:.2f}", line_amount=f"{round(b - min(pv, av), 2):.2f}",
                        note=f"PO ${pv:,.2f} · accepted ${av:,.2f} · billed ${b:,.2f} across {len(bills)} bill(s)" + (f" · ${b - bx:,.2f} of it is a duplicate bill" if b - bx > 0.01 else "")))
    return out
