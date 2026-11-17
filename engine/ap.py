"""Supplier bill checks: every bill line vs the PO line and what we accepted at the dock."""
from common import *

def norm_po(s):
    m = re.search(r"(\d{5})", s or "")
    return f"PO-{m.group(1)}" if m else ""

def pack_n(pack):
    m = re.match(r"(\d+)", pack or "")
    return int(m.group(1)) if m else 1

def run(g):
    sb, po, su, prod = g["sb"], g["po"], g["su"], g["prod"]
    S = su.set_index("quickbooks_vendor_name").to_dict("index")
    SID = su.set_index("supplier_id").to_dict("index")
    P = prod.set_index("supplier_item_code").to_dict("index")
    rows = []
    ev = lambda file, record, shows, expected="": dict(file=file, record=record, shows=shows, expected=expected)
    sb = sb.copy()
    sb["po"] = sb.po_ref.map(norm_po)
    # PO lines: ordered cost and accepted qty summed over shipments
    po = po.copy()
    po["acc"] = po.qty_accepted.map(lambda x: int(x) if x else 0)
    POL = {}
    for (pno, code), grp in po.groupby(["po_no", "supplier_item_code"]):
        h = grp.iloc[0]
        POL[(pno, code)] = dict(po=pno, line=h.po_line, sku=h.sku, cost=float(h.unit_cost), ordered=int(h.qty_ordered),
                                accepted=int(grp.acc.sum()), sup=h.supplier_id, po_total=float(h.po_total),
                                ships=grp, notes="; ".join(x for x in grp.receiving_notes if x))
    PO_BY_CODE = {}
    for (pno, code), v in POL.items():
        PO_BY_CODE.setdefault((v["sup"], code), []).append(v)

    # fill blank / mistyped po refs from the item codes
    for bid, grp in sb.groupby("bill_id"):
        sup = S[grp.iloc[0].vendor]["supplier_id"]
        items = grp[grp.line_type == "ITEM"]
        ok = all((grp.iloc[0].po, c) in POL for c in items.supplier_item_code)
        if not ok:
            cands = {}
            for c in items.supplier_item_code:
                for v in PO_BY_CODE.get((sup, c), []):
                    cands[v["po"]] = cands.get(v["po"], 0) + 1
            if cands:
                best = max(cands, key=cands.get)
                sb.loc[sb.bill_id == bid, "po"] = best

    # duplicate bills: same vendor, same lines, entered more than once
    sig = {}
    for bid, grp in sb.groupby("bill_id", sort=False):
        k = (grp.iloc[0].vendor, tuple(sorted(zip(grp.supplier_item_code, grp.qty, grp.amount))))
        sig.setdefault(k, []).append(bid)
    dup_bills = set()
    for k, bids in sig.items():
        if len(bids) > 1:
            bids = sorted(bids)
            for extra in bids[1:]:
                grp = sb[sb.bill_id == extra]; h = grp.iloc[0]
                first = sb[sb.bill_id == bids[0]].iloc[0]
                dup_bills.add(extra)
                rows.append(dict(kind="DUPBILL", problem="Supplier bill entered twice", bill_id=extra, supplier=S[h.vendor]["supplier_id"],
                                 amount=rnd(grp.amount.astype(float).sum()), date=h.bill_date, cause=f"{h.vendor} bill entered twice",
                                 evidence=[ev("supplier_bills.csv", f"bill {extra}", f"{h.vendor} invoice {h.supplier_invoice_no}, ${float(h.bill_total):,.2f}, {h.status}", "Enter each supplier invoice once"),
                                           ev("supplier_bills.csv", f"bill {bids[0]}", f"{first.vendor} invoice {first.supplier_invoice_no}, ${float(first.bill_total):,.2f}, same lines, {first.status}")]))

    # Rule 7: suppliers announce increases by email; POs placed after the increase carry the new cost.
    # If such a PO still shows the old cost, the bill at the new price is not an overcharge (the PO is stale), so we don't flag it.
    INCREASE = {}
    ib = g.get("ib")
    if ib is not None:
        for _, m in ib[ib.body.str.contains(r"increase about \d+% effective", regex=True)].iterrows():
            mm = re.search(r"increase about (\d+)% effective (\w+ \d+, \d{4})", m.body)
            dom = m.from_email.split("@")[-1]
            for _, s_ in su.iterrows():
                if s_.orders_email.split("@")[-1] == dom:
                    from datetime import datetime
                    INCREASE[s_.supplier_id] = (datetime.strptime(mm.group(2), "%B %d, %Y").date().isoformat(), int(mm.group(1)), m.message_id)
    PODATE = po.groupby("po_no").po_date.first().to_dict()
    billed_cases = {}
    for _, b in sb.iterrows():
        if b.bill_id in dup_bills:
            continue
        sup = S[b.vendor]
        if b.line_type == "FREIGHT":
            v = next((x for x in POL.values() if x["po"] == b.po), None)
            pt = v["po_total"] if v else None
            terms = sup["freight_terms"]
            bad = terms == "ALWAYS_PREPAID" or (terms == "PREPAID_OVER" and pt is not None and pt >= float(sup["free_freight_min"] or 0))
            if bad:
                rows.append(dict(kind="FREIGHT", problem="Freight billed on prepaid order", bill_id=b.bill_id, sku="FREIGHT", po_no=b.po, supplier=sup["supplier_id"],
                                 amount=rnd(float(b.amount)), date=b.bill_date, cause=f"Freight billed against prepaid terms",
                                 evidence=[ev("supplier_bills.csv", f"bill {b.bill_id}, line {b.line_no}", f"FREIGHT ${float(b.amount):,.2f}", "$0.00"),
                                           ev("suppliers.csv", sup["supplier_id"], f"{b.vendor}: freight_terms {terms}" + (f", free over ${float(sup['free_freight_min']):,.0f}" if terms == "PREPAID_OVER" else "")),
                                           ev("purchase_orders.csv", b.po, f"PO total ${pt:,.2f}" if pt else "PO not found")]))
            continue
        v = POL.get((b.po, b.supplier_item_code))
        if not v:
            # supplier changed its item codes (e.g. Tri-State TR36814 -> TN-2611-83): match the PO line by description
            words = set(re.findall(r"[a-z0-9]+", b.description.lower()))
            best = None
            for (pno, code), cand in POL.items():
                if pno != b.po:
                    continue
                cw = set(re.findall(r"[a-z0-9]+", str(cand["ships"].iloc[0].item_description).lower()))
                sc = len(words & cw) / max(1, len(words | cw))
                if best is None or sc > best[0]:
                    best = (sc, cand)
            if best and best[0] >= 0.5:
                v = best[1]
        if not v:
            rows.append(dict(kind="NOPO", problem="Supplier billed with no purchase order", bill_id=b.bill_id, sku=(P.get(b.supplier_item_code, {}).get("sku") or b.supplier_item_code), supplier=sup["supplier_id"], amount=rnd(float(b.amount)), cause=f"Bills with no purchase order behind them",
                             date=b.bill_date, evidence=[ev("supplier_bills.csv", f"bill {b.bill_id}, line {b.line_no}", f"{b.supplier_item_code} {b.qty} {b.uom} ${float(b.amount):,.2f}, po_ref '{b.po_ref}'", "a PO line")]))
            continue
        pk = pack_n(P.get(b.supplier_item_code, {}).get("pack")) if b.uom == "EA" else 1
        cases = float(b.qty) / pk
        unit = rnd(float(b.amount) / cases) if cases else 0
        inc = INCREASE.get(v["sup"])
        stale_po = inc and PODATE.get(v["po"], "") >= inc[0]
        if unit > v["cost"] + 0.011 and not stale_po:
            amt = rnd(float(b.amount) - v["cost"] * cases)
            rows.append(dict(kind="OVERPO", problem="Supplier billed above PO price", bill_id=b.bill_id, sku=v["sku"], po_no=v["po"], supplier=sup["supplier_id"],
                             amount=amt, date=b.bill_date, cause=f"{b.vendor} billing above PO prices",
                             evidence=[ev("supplier_bills.csv", f"bill {b.bill_id}, line {b.line_no}", f"{b.supplier_item_code}: {b.qty} {b.uom} x ${float(b.unit_cost)} = ${float(b.amount):,.2f}" + (f" ({cases:g} cases, ${unit:.2f}/case)" if pk > 1 else ""), f"${v['cost']:.2f} a case"),
                                       ev("purchase_orders.csv", f"{v['po']}, line {v['line']}", f"unit_cost ${v['cost']:.2f}; {v['accepted']} cases accepted")]))
        billed_cases.setdefault((v["po"], v["ships"].iloc[0].supplier_item_code), []).append((b, cases))

    for key, lst in billed_cases.items():
        v = POL[key]
        tot = sum(c for _, c in lst)
        if tot > v["accepted"] + 1e-6:
            extra = tot - v["accepted"]
            b = lst[-1][0]
            sup = S[b.vendor]
            ships = "; ".join(f"{s.receipt_id or 'no receipt'}: received {s.qty_received or 0}, damaged {s.qty_damaged or 0}, accepted {s.qty_accepted or 0} {('(' + s.receiving_notes + ')') if s.receiving_notes else ''}" for _, s in v["ships"].iterrows())
            for bb, c in lst:
                pass
            rows.append(dict(kind="OVERQTYAP", problem="Supplier billed more cases than we accepted", bill_id=b.bill_id, sku=v["sku"], po_no=v["po"], supplier=sup["supplier_id"],
                             amount=rnd(extra * v["cost"]), date=b.bill_date, cause=f"Billed for cases not accepted at the dock",
                             evidence=[ev("supplier_bills.csv", f"bill {bb.bill_id}, line {bb.line_no}", f"{bb.supplier_item_code}: {c:g} cases billed") for bb, c in lst] +
                                      [ev("purchase_orders.csv", f"{v['po']}, line {v['line']}", ships, f"pay for {v['accepted']} cases"),]))

    # bank details
    for bid, grp in sb.groupby("bill_id"):
        h = grp.iloc[0]; sup = S[h.vendor]
        if h.remit_to_account_last4 and h.remit_to_account_last4 != sup["bank_account_last4"]:
            rows.append(dict(kind="BANK", problem="Payment going to unverified bank account", bill_id=bid, supplier=sup["supplier_id"],
                             amount=rnd(float(h.bill_total)), date=h.bill_date, cause=f"{h.vendor} payments redirected to account ...{h.remit_to_account_last4}",
                             evidence=[ev("supplier_bills.csv", f"bill {bid}", f"${float(h.bill_total):,.2f} {h.status}, remit to account ...{h.remit_to_account_last4}", f"account ...{sup['bank_account_last4']}"),
                                       ev("suppliers.csv", sup["supplier_id"], f"bank on file {sup['bank_name']} ...{sup['bank_account_last4']}, verified {sup['bank_verified_on']}, phone {sup['phone']}")]))
    return rows
