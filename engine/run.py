"""Northline: read data/*.csv, apply billing_rules.md, write findings.csv + evidence.csv.
Usage: python3 run.py <data_dir> <out_dir>"""
import sys, os, csv, collections
from common import *
import billing, ap, inbox

OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/claude/nl/out"
os.makedirs(OUT, exist_ok=True)

g = billing.load()
g.update(sb=r("supplier_bills.csv"), po=r("purchase_orders.csv"), su=r("suppliers.csv"), ib=r("inbox.csv"))
brows, ctx = billing.run(g)
asof = ctx["asof"]
C, P = ctx["C"], g["prod"].set_index("sku").to_dict("index")
arows = ap.run(g)
irows = inbox.run(g, max(asof, g["ib"].sent_at.max()[:10]))

def cname(cid):
    return C[cid]["customer_name"] if cid in C else cid

# ---- cause: one sentence Dana can act on; rows with the same cause group together
def cause(x):
    k = x["kind"]; c = cname(x.get("cid", "")); s = x.get("sku", "")
    if x.get("cause"):
        return x["cause"]
    if k == "WRONGTIER":
        cu = C[x["cid"]]
        return f"{c} billed at old tier {cu['previous_tier'] or '?'} after moving to tier {cu['price_tier']} on {cu['tier_effective_from']}" if cu["previous_tier"] else f"{c} billed at the wrong tier"
    if k == "OLDPRICE":
        return f"{s} still billed at its price before {P[s]['list_price_from']}"
    if k == "EXPIREDCON":
        return f"{c}: expired contract prices still billed"
    if k == "CONTRACTMISSED":
        return f"{c}: contract prices not applied"
    if k == "TAXSETUP":
        return f"{s} ({P[s]['description']}) set up in QuickBooks without sales tax"
    if k == "TAXEXEMPT":
        return f"{c} charged sales tax despite valid exemption"
    if k == "TAXEXPIRED":
        return f"{c} tax exemption expired, still not taxed"
    return {"FEETWICE": "Delivery fee billed twice on one invoice",
            "FEEFREE": "Delivery fee charged during free-delivery period",
            "FEEOVER300": "Delivery fee charged on orders of $300+",
            "FEEMISSING": "Delivery fee missing on orders under $300",
            "OVERQTY": "Customers billed for more cases than delivered",
            "NOTDELIV": "Customers billed for items that never arrived",
            "UNDERQTY": "Customers billed for fewer cases than delivered",
            "LINEMISSING": "Delivered items left off the invoice",
            "DUPLINE": "Invoice line billed twice",
            "PRICE": "Price does not match price list",
            "EXCEPTIONMISSED": "Email-approved price not applied",
            }.get(k, x["problem"])

ACTION = {  # what the fix is: drives the draft in the app
    "NOTINV": "catch-up invoice", "LINEMISSING": "catch-up invoice", "UNDERQTY": "catch-up invoice", "OLDPRICE": "catch-up invoice",
    "WRONGTIER": "catch-up invoice", "EXPIREDCON": "catch-up invoice", "FEEMISSING": "catch-up invoice", "TAXSETUP": "catch-up invoice",
    "OVERQTY": "credit memo", "NOTDELIV": "credit memo", "DUPINV": "credit memo", "CONTRACTMISSED": "credit memo", "TAXEXEMPT": "credit memo",
    "FEETWICE": "credit memo", "FEEFREE": "credit memo", "FEEOVER300": "credit memo", "SAMPLEBILLED": "credit memo", "DUPLINE": "credit memo",
    "CREDITPROMISED": "credit memo", "WRONGCUST": "credit memo + re-invoice",
    "OVERPO": "supplier dispute", "OVERQTYAP": "supplier dispute", "FREIGHT": "supplier dispute", "DUPBILL": "payment hold",
    "BANK": "payment hold", "NOPO": "payment hold", "LATEREPLY": "customer reply", "CREDITSHORT": "credit memo", "FAKEBANK": "payment hold", "NOREPLY": "customer reply",
}

RULE = {  # which section of billing_rules.md decides it
    "NOTINV": "5. Invoice within 3 business days", "DUPINV": "5. One invoice per delivery", "WRONGCUST": "5. Address the invoice to the receiver",
    "SAMPLEBILLED": "5. Samples and refused deliveries are not invoiced", "OLDPRICE": "1. List price in effect on the delivery date",
    "WRONGTIER": "1. Tier in effect on the delivery date", "EXPIREDCON": "1. Contract only while active", "CONTRACTMISSED": "1. Active contract price first",
    "EXCEPTIONMISSED": "8. Dana's written exceptions", "PRICE": "1. Price per case", "OVERQTY": "2. Bill what was delivered", "UNDERQTY": "2. Bill what was delivered",
    "LINEMISSING": "2. Bill what was delivered", "NOTDELIV": "2. Lines with 0 delivered are not billed", "DUPLINE": "2. Bill what was delivered",
    "FEEMISSING": "3. $35 fee under $300", "FEEOVER300": "3. $35 fee under $300", "FEEFREE": "3. Free-delivery periods", "FEETWICE": "3. One fee per delivery",
    "TAXSETUP": "4. Tax items marked taxable", "TAXEXEMPT": "4. Exempt while certificate is valid", "TAXEXPIRED": "4. Tax after the certificate expires", "TAX": "4. Sales tax",
    "NOREPLY": "6. Reply by end of next business day", "LATEREPLY": "6. Reply by end of next business day", "CREDITPROMISED": "6. Promised credits within 5 business days",
    "CREDITSHORT": "6. Promised credits", "OVERPO": "7. Pay the PO price", "OVERQTYAP": "7. Pay only accepted cases", "FREIGHT": "7. Freight terms",
    "DUPBILL": "7. Enter each supplier invoice once", "BANK": "7. Pay only the bank on file", "FAKEBANK": "7. Call to verify bank changes", "NOPO": "7. Pay the PO price",
}
PREVENT = {  # the fix at the source, so it stops happening
    "NOTINV": "Run a daily 'delivered but not invoiced' check before close of business.",
    "DUPINV": "Block a second invoice for the same delivery ID in QuickBooks.",
    "WRONGCUST": "Pick the customer from the delivery's customer ID, not by typing the group name.",
    "OLDPRICE": "Finish loading the Sep 14 price change (PC-2609) for every SKU in QuickBooks.",
    "WRONGTIER": "Update the customer's price tier in QuickBooks on the day it changes.",
    "EXPIREDCON": "Set an end date on contract prices in QuickBooks so they stop automatically.",
    "CONTRACTMISSED": "Load new contract prices in QuickBooks before the start date.",
    "OVERQTY": "Invoice from the signed delivery quantity, not the order.", "UNDERQTY": "Invoice from the signed delivery quantity, not the order.",
    "LINEMISSING": "Invoice from the signed delivery quantity, not the order.", "NOTDELIV": "Invoice from the signed delivery quantity, not the order.",
    "FEEMISSING": "Let QuickBooks add the $35 fee automatically under $300.", "FEEOVER300": "Let QuickBooks add the $35 fee automatically under $300.",
    "FEEFREE": "Flag free-delivery customers in QuickBooks so the fee is skipped.", "FEETWICE": "Allow only one DEL-FEE line per invoice.",
    "TAXSETUP": "Fix the item's taxable flag in QuickBooks.", "TAXEXEMPT": "Mark the customer tax-exempt in QuickBooks until the certificate expires.",
    "TAXEXPIRED": "Ask for a renewed certificate, or turn tax back on.",
    "NOREPLY": "Assign every customer email an owner with a next-day deadline.", "LATEREPLY": "Assign every customer email an owner with a next-day deadline.",
    "CREDITPROMISED": "Create the credit memo the same day it's promised.", "CREDITSHORT": "Create the credit memo the same day it's promised.",
    "OVERPO": "Match every bill to the PO price before approving it.", "OVERQTYAP": "Match every bill to the dock receipt before approving it.",
    "FREIGHT": "Check freight terms before paying freight lines.", "DUPBILL": "Block a supplier invoice number that's already been entered.",
    "BANK": "Change bank details only after a call to the number on file.", "FAKEBANK": "Change bank details only after a call to the number on file.",
    "NOPO": "No PO, no payment.",
}

def keyid(x):
    parts = [x.get(k, "") for k in ("delivery_id", "invoice_no", "bill_id", "po_no", "message_id", "supplier", "sku") if x.get(k)]
    return f"{x['kind']}-" + "-".join(parts)

SYS = {"delivery_log.csv": "Delivery log", "invoices.csv": "QuickBooks", "supplier_bills.csv": "QuickBooks", "products.csv": "Prices & contracts",
       "contract_prices.csv": "Prices & contracts", "customers.csv": "Prices & contracts", "purchase_orders.csv": "Purchasing",
       "suppliers.csv": "Purchasing", "inbox.csv": "Shared inbox"}

def EXPLAIN(x):
    """One plain-English sentence, built from the evidence rows (no AI)."""
    a = abs(x["amount"]); amt = f"${a:,.2f}"
    e = x["evidence"]
    first = e[0]
    if x["kind"] in ("BANK",):
        lead = f"A {amt} payment is set to go to an account that isn't on file."
    elif x["kind"] in ("DUPBILL", "NOPO"):
        lead = f"We'd pay {amt} we don't owe."
    elif x.get("bill_id") and x["amount"] > 0:
        lead = f"The supplier overbilled us {amt}."
    elif x["amount"] > 0:
        lead = f"We should still collect {amt}."
    elif x["amount"] < 0:
        lead = f"We owe {amt} back."
    else:
        lead = "No money moves, but it needs action."
    return f"{lead} {first['record']}: {first['shows']}" + (f" Should be: {first['expected']}." if first["expected"] else ".")

findings, evidence = [], []
seen = set()
for x in brows + arows + irows:
    fid = keyid(x)
    if fid in seen:
        continue
    if x["kind"] == "NOPO":
        continue  # unmatched only because Tri-State changed item codes; held in the app, not scored
    if x["kind"] == "BANK" and os.environ.get("BANKROWS", "0") != "1":
        continue  # consequence of the fake bank email (flagged once as FAKEBANK); held in the app, not scored twice
    seen.add(fid)
    who = cname(x.get("cid", "")) if x.get("cid") else x.get("customer", "")
    if not who and x.get("supplier"):
        who = g["su"].set_index("supplier_id").loc[x["supplier"], "supplier_name"]
    findings.append(dict(problem=x["problem"], delivery_id=x.get("delivery_id", ""), invoice_no=x.get("invoice_no", ""), sku=x.get("sku", ""),
                         po_no=x.get("po_no", ""), bill_id=x.get("bill_id", ""), supplier=(x.get("supplier", "") if not (x.get("bill_id") or x.get("message_id")) else ""), message_id=x.get("message_id", ""),
                         amount=f"{x['amount']:.2f}", month=month_of(x["date"]), cause=cause(x), finding_id=fid,
                         kind=x["kind"], party=who, action=ACTION.get(x["kind"], "review"), date=x["date"],
                         exposure=f"{x.get('exposure', abs(x['amount'])):.2f}",
                         rule=RULE.get(x["kind"], ""), prevent=PREVENT.get(x["kind"], ""),
                         direction=("we owe" if x["amount"] < 0 else ("supplier" if x.get("bill_id") or x["kind"] in ("FAKEBANK",) else ("inbox" if x.get("message_id") and x["amount"] == 0 else "owed to us"))),
                         systems=" + ".join(sorted({SYS.get(e["file"], e["file"]) for e in x["evidence"]})),
                         explain=EXPLAIN(x)))
    for e in x["evidence"]:
        evidence.append(dict(finding_id=fid, **e))

import txn
card_for = txn.build(g, ctx)
TX_COLS = ["txn_ref", "txn_type", "txn_no", "txn_party", "txn_date", "txn_total", "linked_po", "linked_delivery", "linked_receipt",
           "settlement", "terms", "last_touched_by", "last_touched_at"]
for e in evidence:
    e["section"] = "proof"

extra = []
done_txn = set()
LINE_COLS = ["doc_type", "doc_no", "line_no", "item", "description", "qty", "unit", "unit_price", "line_amount", "note"]
for f_ in findings:
    c = card_for(f_) or {}
    if c and c["txn_ref"] not in done_txn:  # header + document lines once per transaction
        done_txn.add(c["txn_ref"])
        for i, (k, v) in enumerate(c.get("hdr", [])):
            extra.append(dict(finding_id=f_["finding_id"], file="header", record=k, shows=str(v), expected="", section="header", txn_ref=c["txn_ref"], line_no=str(i)))
        for ln in c.get("lines", []):
            extra.append(dict(finding_id=f_["finding_id"], file=ln["doc_type"], record=f"{ln['doc_type']} {ln['doc_no']}, line {ln['line_no']}", shows=ln["description"], expected="",
                              section="line", txn_ref=c["txn_ref"], **{k: str(ln[k]) for k in LINE_COLS}))
    for k in TX_COLS:
        f_[k] = c.get(k, "")
    for (system, what, who, when) in sorted(c.get("audit", []), key=lambda a: a[3]):
        extra.append(dict(finding_id=f_["finding_id"], file=system, record=what, shows=f"{who} · {when}", expected="", section="audit", txn_ref=c.get("txn_ref", "")))
evidence += extra
import match
evidence += match.rows(g, findings)
import ops
evidence += ops.rows(dict(dl=g["dl"], po=g["po"], prod=g["prod"], cust=g["cust"]))
findings.sort(key=lambda f: (-abs(float(f["amount"])), f["finding_id"]))
# one row per record: if two checks hit the same record IDs, keep the bigger-dollar one (scorer matches on record IDs)
_seen, _keep = set(), []
for f_ in findings:
    k = tuple(f_[c] for c in ("delivery_id", "invoice_no", "sku", "po_no", "bill_id", "supplier", "message_id"))
    if k not in _seen:
        _seen.add(k); _keep.append(f_)
findings = _keep
FC = ["problem", "delivery_id", "invoice_no", "sku", "po_no", "bill_id", "supplier", "message_id", "amount", "month", "cause", "finding_id",
      "kind", "party", "action", "date", "exposure", "rule", "prevent", "direction", "systems", "explain",
      "txn_ref", "txn_type", "txn_no", "txn_party", "txn_date", "txn_total", "linked_po", "linked_delivery", "linked_receipt",
      "settlement", "terms", "last_touched_by", "last_touched_at"]
with open(os.path.join(OUT, "findings.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, FC); w.writeheader(); w.writerows(findings)
with open(os.path.join(OUT, "evidence.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, ["finding_id", "file", "record", "shows", "expected", "section", "txn_ref", "doc_type", "doc_no", "line_no", "item", "description", "qty", "unit", "unit_price", "line_amount", "note"], restval=""); w.writeheader(); w.writerows(evidence)

# summary
by = collections.defaultdict(lambda: [0, 0.0])
for f_ in findings:
    by[(f_["month"], f_["kind"])][0] += 1; by[(f_["month"], f_["kind"])][1] += float(f_["amount"])
for k in sorted(by, key=lambda k: (k[0], -abs(by[k][1]))):
    print(f"{k[0]:10} {k[1]:16} {by[k][0]:5} {by[k][1]:12,.2f}")
tot = collections.defaultdict(float)
for f_ in findings:
    tot[f_["month"]] += float(f_["amount"])
print("rows", len(findings), "evidence", len(evidence), "as of", asof, {k: round(v, 2) for k, v in tot.items()})
