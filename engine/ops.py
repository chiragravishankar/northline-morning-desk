"""Operations (inventory & fulfillment): stock movements and fulfillment exceptions. Not money findings,
so they go to evidence.csv (section ops / flow), never to findings.csv."""
from common import *

def rows(g):
    dl, po, prod, cu = g["dl"], g["po"], g["prod"], g["cust"]
    P = prod.set_index("sku").to_dict("index"); C = cu.set_index("customer_id").to_dict("index")
    out = []
    def add(fid, kind, record, shows, **k):
        out.append(dict(finding_id=fid, file=kind, record=record, shows=shows, expected="", section="ops", **k))
    for _, x in dl[(dl.short_reason != "") | (dl.delivery_status != "DELIVERED")].iterrows():
        short = int(x.qty_ordered or 0) - int(x.qty_delivered or 0)
        add(f"OPS-{x.delivery_id}-{x.sku}", x.short_reason or x.delivery_status, f"Delivery {x.delivery_id}, line {x.line_no}",
            f"{C.get(x.customer_id, {}).get('customer_name', x.ship_to_name)}: {x.sku} {x.item_description}; ordered {x.qty_ordered}, shipped {x.qty_shipped}, delivered {x.qty_delivered}",
            txn_ref=x.delivery_id, doc_type="Delivery note", doc_no=x.delivery_id, line_no=x.line_no, item=x.sku, description=x.item_description,
            qty=str(short), unit=x.uom, note=f"{x.delivery_date}, route {x.route_id}, driver {x.driver}, {x.delivery_status}")
    for _, x in po[(po.receiving_notes != "")].iterrows():
        add(f"OPS-{x.po_no}-{x.po_line}-{x.receipt_id or 'open'}", x.receiving_notes, f"{x.po_no}, line {x.po_line}",
            f"{x.supplier_name}: {x.sku} {x.item_description}; ordered {x.qty_ordered}, received {x.qty_received or 0}, damaged {x.qty_damaged or 0}, accepted {x.qty_accepted or 0}",
            txn_ref=x.po_no, doc_type="Purchase order", doc_no=x.po_no, line_no=x.po_line, item=x.sku, description=x.item_description,
            qty=str(int(x.qty_ordered or 0) - int(x.qty_accepted or 0)), unit="CS", note=f"expected {x.expected_date}" + (f", received {x.received_date} by {x.received_by}" if x.received_date else ""))
    # stock flow per SKU: cases in (accepted at dock) vs cases out (delivered)
    inn = po.assign(a=po.qty_accepted.replace("", "0").astype(int)).groupby("sku").a.sum()
    open_ = po[po.receipt_id == ""].assign(q=lambda d: d.qty_ordered.astype(int)).groupby("sku").q.sum()
    outq = dl.assign(q=dl.qty_delivered.replace("", "0").astype(int)).groupby("sku").q.sum()
    shorts = dl[dl.short_reason == "Out of stock"].groupby("sku").size()
    for sku in sorted(set(inn.index) | set(outq.index)):
        p = P.get(sku, {})
        out.append(dict(finding_id=f"FLOW-{sku}", file="Stock flow", record=sku, shows=p.get("description", ""), expected="", section="flow",
                        txn_ref=sku, item=sku, description=p.get("description", ""), qty=str(int(inn.get(sku, 0))), unit_price=str(int(outq.get(sku, 0))),
                        line_amount=str(int(open_.get(sku, 0))), note=f"stock-outs {int(shorts.get(sku, 0))}; zone {p.get('storage_zone','')}; supplier {p.get('supplier_id','')}",
                        doc_type="Stock flow", doc_no=p.get("category", ""), line_no="", unit="CS"))
    return out
