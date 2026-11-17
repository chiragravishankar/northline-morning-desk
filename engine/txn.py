"""Transaction cards: for every flagged invoice / bill / delivery / email, our own reference ID,
links to the PO, delivery note and dock receipt, settlement status, contract terms and an audit trail.
All of it comes from the raw files; the app only loads findings.csv + evidence.csv."""
import hashlib, re
from common import *

def ref(kind, key):
    h = hashlib.sha1(f"{kind}|{key}".encode()).hexdigest()[:6].upper()
    return f"NL-{kind}-{h}"

def build(g, ctx):
    inv, dl, sb, po, su, cu, con, ib = g["inv"], g["dl"], g["sb"], g["po"], g["su"], g["cust"], g["con"], g["ib"]
    C = cu.set_index("customer_id").to_dict("index")
    QB = {r["quickbooks_name"]: k for k, r in C.items()}
    S = su.set_index("quickbooks_vendor_name").to_dict("index")
    inv2d = ctx["inv2d"]
    d2inv = {}
    for i, (dd, _) in inv2d.items():
        d2inv.setdefault(dd, []).append(i)
    invs = inv[inv.transaction_type == "Invoice"]
    cms = inv[inv.transaction_type == "Credit Memo"]
    sbn = sb.copy(); sbn["pon"] = sbn.po_ref.map(lambda s: (lambda m: f"PO-{m.group(1)}" if m else "")(re.search(r"(\d{5})", s or "")))

    def mails(token):
        if not token:
            return ib.iloc[0:0]
        return ib[ib.subject.str.contains(token, regex=False) | ib.body.str.contains(token, regex=False)]

    def card_invoice(ino):
        L = invs[invs.invoice_no == ino]
        if L.empty:
            return None
        h = L.iloc[0]
        did = inv2d.get(ino, ("", ""))[0]
        cid = QB.get(h.customer, "")
        c = C.get(cid, {})
        cm = cms[cms.invoice_no == ino]
        audit = [("QuickBooks", f"Invoice {ino} created", h.created_by, h.created_at)]
        for _, x in cm.drop_duplicates("credit_memo_no").iterrows():
            audit.append(("QuickBooks", f"Credit memo {x.credit_memo_no} ({x.reason_code}) ${float(x.total):,.2f}", x.created_by, x.created_at))
        if did:
            D = dl[dl.delivery_id == did].iloc[0]
            audit.append(("Delivery log", f"Delivered {did}, signed by {D.signed_by}", D.driver, f"{D.delivery_date} {D.pod_time}"))
        for _, m in mails(ino).iterrows():
            audit.append(("Shared inbox", f"Email '{m.subject}'", m.from_email, m.sent_at))
        cons = con[(con.customer_id == cid)]
        hdr = [("Customer", f"{h.customer} ({cid})"), ("Invoice date", h.date), ("Due date", h.due_date), ("Payment terms", h.terms),
               ("Status", h.status), ("Subtotal", f"${float(h.subtotal):,.2f}"), ("Sales tax", f"${float(h.tax):,.2f}"), ("Total", f"${float(h.total):,.2f}"),
               ("Balance due", f"${float(h.balance or 0):,.2f}"), ("Customer PO", h.customer_po or "None"), ("Ship date", h.ship_date or "Blank"),
               ("Memo", h.memo or "Blank"), ("Sales rep", h.sales_rep), ("Created by", f"{h.created_by} · {h.created_at}"),
               ("Price tier", c.get("price_tier", "?")), ("Customer type", c.get("customer_type", ""))]
        lines = [dict(doc_type="Invoice", doc_no=ino, line_no=x.line_no, item=x["item"], description=x.item_description, qty=x.qty, unit="CS",
                      unit_price=x.rate, line_amount=x.amount, note=f"tax ${float(x.line_tax or 0):.2f}" if float(x.line_tax or 0) else "") for _, x in L.iterrows()]
        lines += [dict(doc_type="Credit memo", doc_no=x.credit_memo_no, line_no=x.line_no, item=x["item"], description=x.item_description, qty=x.qty, unit="CS",
                       unit_price=x.rate, line_amount=x.amount, note=x.reason_code) for _, x in cm.iterrows()]
        ddate = dl[dl.delivery_id == did].iloc[0].delivery_date if did else (h.ship_date or h.date)
        for _, x in L.iterrows():
            if x["item"] == "DEL-FEE":
                pb = ("Rule 3", "Delivery fee $35.00 when merchandise is under $300 at correct prices", "35.00", "")
            else:
                try:
                    up, why, src = ctx["price"](cid, x["item"], ddate)
                except Exception:
                    continue
                pr = ctx["P"].get(x["item"], {})
                if src == "contract":
                    cc = [c for c in ctx["CON"].get((cid, x["item"]), []) if c.start_date <= ddate and (c.end_date == "" or ddate <= c.end_date)][0]
                    pb = (f"Contract {cc.contract_id}", f"${float(cc.contract_price):.2f}/case, {cc.start_date} to {cc.end_date or 'open'}, signed {cc.signed_on}, approved by {cc.approved_by}" + (f", {cc.notes}" if cc.notes else ""), f"{up:.2f}", cc.contract_id)
                elif src == "exception":
                    pb = ("Email approval", why, f"{up:.2f}", "")
                else:
                    pb = (f"Price list {pr.get('price_change_id','')}", f"{why}. List ${float(pr.get('list_price') or 0):.2f} from {pr.get('list_price_from','')}" + (f", before that ${float(pr['previous_list_price']):.2f}" if pr.get("previous_list_price") else "") + f"; taxable {pr.get('taxable','')}", f"{up:.2f}", pr.get("price_change_id", ""))
            lines.append(dict(doc_type="Price basis", doc_no=pb[0], line_no=x.line_no, item=x["item"], description=pb[1], qty="", unit="", unit_price=pb[2], line_amount="",
                              note=f"billed ${float(x.rate):.2f}" + ("" if abs(float(x.rate) - float(pb[2])) < 0.005 else f" (difference ${float(x.rate) - float(pb[2]):+.2f}/case)")))
        if did:
            lines += [dict(doc_type="Delivery note", doc_no=did, line_no=x.line_no, item=x.sku, description=x.item_description, qty=x.qty_delivered, unit=x.uom,
                           unit_price="", line_amount="", note=f"ordered {x.qty_ordered}, shipped {x.qty_shipped}" + (f", {x.short_reason}" if x.short_reason else "") + f", {x.delivery_status}")
                      for _, x in dl[dl.delivery_id == did].iterrows()]
        return dict(hdr=hdr, lines=lines, txn_ref=ref("INV", ino), txn_type="Customer invoice", txn_no=ino,
                    txn_party=h.customer, txn_date=h.date, txn_total=f"{float(h.total):.2f}",
                    linked_po=h.customer_po, linked_delivery=did, linked_receipt="",
                    settlement=f"{h.status}" + (f", ${float(h.balance):,.2f} unpaid" if float(h.balance or 0) > 0 else ", fully paid") + f", due {h.due_date}",
                    terms=f"{h.terms}; tier {c.get('price_tier','?')}" + (f" (was {c['previous_tier']} before {c['tier_effective_from']})" if c.get("previous_tier") else "")
                          + (f"; {len(cons)} contract prices" if len(cons) else "") + (f"; tax-exempt to {c['exempt_cert_expires']}" if c.get("tax_exempt") == "Y" else "")
                          + (f"; free delivery from {c['free_delivery_from']}" if c.get("free_delivery_from") else ""),
                    last_touched_by=sorted(audit, key=lambda a: a[3])[-1][2], last_touched_at=sorted(audit, key=lambda a: a[3])[-1][3], audit=audit)

    def card_bill(bid):
        L = sbn[sbn.bill_id == bid]
        if L.empty:
            return None
        h = L.iloc[0]; s = S.get(h.vendor, {})
        P = po[po.po_no == h.pon]
        rec = ", ".join(sorted(set(x for x in P.receipt_id if x)))
        audit = [("QuickBooks", f"Bill {bid} entered (supplier invoice {h.supplier_invoice_no}, PO typed '{h.po_ref}')", h.entered_by, h.bill_date)]
        if len(P):
            p0 = P.iloc[0]
            audit.append(("Purchasing", f"{h.pon} placed, ${float(p0.po_total):,.2f}", p0.buyer, p0.po_date))
            for _, r in P[P.receipt_id != ""].drop_duplicates("receipt_id").iterrows():
                audit.append(("Purchasing", f"Dock receipt {r.receipt_id} ({r.carrier})", r.received_by, r.received_date))
        if h.paid_date:
            audit.append(("QuickBooks", f"Paid by {h.payment_method} to account ...{h.remit_to_account_last4}", "AP", h.paid_date))
        for _, m in mails(h.supplier_invoice_no).iterrows():
            audit.append(("Shared inbox", f"Email '{m.subject}'", m.from_email, m.sent_at))
        last = sorted(audit, key=lambda a: a[3])[-1]
        hdr = [("Supplier", f"{h.vendor} ({s.get('supplier_id','')})"), ("Supplier invoice", h.supplier_invoice_no), ("Bill date", h.bill_date), ("Due date", h.due_date),
               ("Payment terms", h.terms), ("Status", h.status), ("Bill total", f"${float(h.bill_total):,.2f}"), ("Paid on", h.paid_date or "Not paid"),
               ("Scheduled pay date", h.scheduled_pay_date or "None"), ("Pay to account", f"...{h.remit_to_account_last4}"), ("Bank on file", f"...{s.get('bank_account_last4','')} ({s.get('bank_name','')})"),
               ("PO typed by AP", h.po_ref or "Blank"), ("Matched PO", h.pon or "None"), ("Freight terms", s.get("freight_terms", "")), ("Entered by", h.entered_by),
               ("Supplier phone", s.get("phone", ""))]
        lines = [dict(doc_type="Supplier bill", doc_no=bid, line_no=x.line_no, item=x.supplier_item_code, description=x.description, qty=x.qty, unit=x.uom,
                      unit_price=x.unit_cost, line_amount=x.amount, note=x.line_type) for _, x in L.iterrows()]
        lines += [dict(doc_type="Purchase order", doc_no=x.po_no, line_no=x.po_line, item=x.supplier_item_code, description=f"{x.sku} {x.item_description}", qty=x.qty_ordered, unit="CS",
                       unit_price=x.unit_cost, line_amount=x.line_amount, note=f"PO date {x.po_date}, buyer {x.buyer}") for _, x in P.drop_duplicates(["po_line"]).iterrows()]
        lines += [dict(doc_type="Dock receipt", doc_no=x.receipt_id or "Not received", line_no=x.po_line, item=x.supplier_item_code, description=x.item_description, qty=x.qty_accepted or "0", unit="CS",
                       unit_price="", line_amount="", note=f"received {x.qty_received or 0}, damaged {x.qty_damaged or 0}, accepted {x.qty_accepted or 0}" + (f", {x.receiving_notes}" if x.receiving_notes else "") + (f", {x.received_date} by {x.received_by}" if x.received_date else ""))
                  for _, x in P.iterrows()]
        inc = ib[ib.from_email.str.endswith("@" + s.get("orders_email", "x@none").split("@")[-1]) & ib.body.str.contains("increase", case=False)]
        for _, x in L[L.line_type == "ITEM"].iterrows():
            pl = P[P.supplier_item_code == x.supplier_item_code]
            if pl.empty:
                continue
            p0 = pl.iloc[0]
            note = f"PO {p0.po_no} dated {p0.po_date}, buyer {p0.buyer}"
            for _, m in inc.iterrows():
                note += f"; supplier price increase email {m.message_id} ({m.sent_at[:10]})"
            lines.append(dict(doc_type="Price basis", doc_no=f"PO {p0.po_no} line {p0.po_line}", line_no=x.line_no, item=x.supplier_item_code,
                              description=f"Agreed PO cost ${float(p0.unit_cost):.2f}/case (rule 7: the PO price holds)", qty="", unit="", unit_price=f"{float(p0.unit_cost):.2f}", line_amount="",
                              note=note + f"; billed ${float(x.unit_cost)} per {x.uom}"))
        return dict(hdr=hdr, lines=lines, txn_ref=ref("BILL", bid), txn_type="Supplier bill", txn_no=f"{bid} / {h.supplier_invoice_no}",
                    txn_party=h.vendor, txn_date=h.bill_date, txn_total=f"{float(h.bill_total):.2f}",
                    linked_po=h.pon, linked_delivery="", linked_receipt=rec,
                    settlement=f"{h.status}" + (f", paid {h.paid_date}" if h.paid_date else (f", scheduled {h.scheduled_pay_date}" if h.scheduled_pay_date else ", unpaid")) + f", due {h.due_date}, to account ...{h.remit_to_account_last4}",
                    terms=f"{h.terms}; freight {s.get('freight_terms','?')}" + (f" (free over ${float(s['free_freight_min']):,.0f})" if s.get("freight_terms") == "PREPAID_OVER" else "") + f"; bank on file ...{s.get('bank_account_last4','?')}",
                    last_touched_by=last[2], last_touched_at=last[3], audit=audit)

    def card_delivery(did):
        D = dl[dl.delivery_id == did]
        if D.empty:
            return None
        h = D.iloc[0]; c = C.get(h.customer_id, {})
        audit = [("Delivery log", f"Order {h.order_id} taken ({h.order_channel})", "orders@", h.order_date),
                 ("Delivery log", f"Delivered on route {h.route_id}, truck {h.truck_id}, signed by {h.signed_by}", h.driver, f"{h.delivery_date} {h.pod_time}")]
        for _, m in mails(h.order_id).iterrows():
            audit.append(("Shared inbox", f"Email '{m.subject}'", m.from_email, m.sent_at))
        last = sorted(audit, key=lambda a: a[3])[-1]
        hdr = [("Customer", f"{c.get('customer_name', h.ship_to_name)} ({h.customer_id})"), ("Order", h.order_id), ("Order type", h.order_type), ("Order date", h.order_date),
               ("Delivery date", h.delivery_date), ("Route / stop", f"{h.route_id} / {h.stop_no}"), ("Driver", h.driver), ("Signed by", f"{h.signed_by} at {h.pod_time}"),
               ("Ship to", h.ship_to_address), ("Payment terms", c.get("payment_terms", "")), ("Price tier", c.get("price_tier", "")), ("Invoice", ", ".join(d2inv.get(did, [])) or "None")]
        lines = [dict(doc_type="Delivery note", doc_no=did, line_no=x.line_no, item=x.sku, description=x.item_description, qty=x.qty_delivered, unit=x.uom, unit_price="", line_amount="",
                      note=f"ordered {x.qty_ordered}, shipped {x.qty_shipped}" + (f", {x.short_reason}" if x.short_reason else "") + f", {x.delivery_status}") for _, x in D.iterrows()]
        return dict(hdr=hdr, lines=lines, txn_ref=ref("DEL", did), txn_type="Delivery", txn_no=did, txn_party=c.get("customer_name", h.ship_to_name), txn_date=h.delivery_date,
                    txn_total="", linked_po=h.order_id, linked_delivery=did, linked_receipt="",
                    settlement="Not invoiced" if not d2inv.get(did) else f"Invoiced on {', '.join(d2inv[did])}",
                    terms=f"{c.get('payment_terms','?')}; tier {c.get('price_tier','?')}", last_touched_by=last[2], last_touched_at=last[3], audit=audit)

    def card_mail(mid):
        M = ib[ib.message_id == mid]
        if M.empty:
            return None
        h = M.iloc[0]
        T = ib[ib.thread_id == h.thread_id].sort_values("sent_at")
        audit = [("Shared inbox", f"{x.direction}: '{x.subject}'", x.from_email, x.sent_at) for _, x in T.iterrows()]
        last = audit[-1]
        hdr = [("From", f"{h.from_name} <{h.from_email}>"), ("Mailbox", h.mailbox), ("Subject", h.subject), ("Received", h.sent_at), ("Thread", h.thread_id)]
        lines = [dict(doc_type="Email", doc_no=x.message_id, line_no=str(i + 1), item=x.direction, description=x.subject, qty="", unit="", unit_price="", line_amount="",
                      note=f"{x.from_name}, {x.sent_at}: {x.body[:300]}") for i, (_, x) in enumerate(T.iterrows())]
        return dict(hdr=hdr, lines=lines, txn_ref=ref("MSG", mid), txn_type="Email", txn_no=f"{mid} (thread {h.thread_id})", txn_party=h.from_name, txn_date=h.sent_at[:10], txn_total="",
                    linked_po="", linked_delivery="", linked_receipt="", settlement=f"{len(T)} messages in thread", terms="Reply by end of next business day",
                    last_touched_by=last[2], last_touched_at=last[3], audit=audit)

    cache = {}
    def card_for(f):
        if f.get("bill_id"):
            k = ("b", f["bill_id"]); fn = lambda: card_bill(f["bill_id"])
        elif f.get("invoice_no"):
            k = ("i", f["invoice_no"]); fn = lambda: card_invoice(f["invoice_no"])
        elif f.get("delivery_id"):
            k = ("d", f["delivery_id"]); fn = lambda: card_delivery(f["delivery_id"])
        elif f.get("message_id"):
            k = ("m", f["message_id"]); fn = lambda: card_mail(f["message_id"])
        else:
            return None
        if k not in cache:
            cache[k] = fn()
        return cache[k]
    return card_for
