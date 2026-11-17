"""Customer billing checks: every delivery vs the QuickBooks invoice that should bill it."""
from common import *

def load():
    g = {}
    g["cust"] = r("customers.csv"); g["con"] = r("contract_prices.csv"); g["prod"] = r("products.csv")
    g["dl"] = r("delivery_log.csv"); g["inv"] = r("invoices.csv")
    return g

def run(g, exceptions=None, asof=None):
    exceptions = exceptions or {}
    cust, con, prod, dl, inv = g["cust"], g["con"], g["prod"], g["dl"], g["inv"]
    C = cust.set_index("customer_id").to_dict("index")
    QB = {row["quickbooks_name"]: cid for cid, row in C.items()}
    P = prod.set_index("sku").to_dict("index")
    CON = {}
    for _, c in con.iterrows():
        CON.setdefault((c.customer_id, c.sku), []).append(c)

    from exceptions import APPROVED
    def price(cid, sku, dd):
        """Correct unit price + the evidence for it."""
        for ex in APPROVED:
            if ex["type"] == "price" and ex["customer_id"] == cid and ex["sku"] == sku and ex["start"] <= dd <= ex["end"]:
                return money(ex["price"]), f"Dana approved ${ex['price']:.2f} a case by email from {ex['start']} ({ex['msg']})", "exception"
        for c in CON.get((cid, sku), []):
            if c.start_date <= dd and (c.end_date == "" or dd <= c.end_date):
                return money(c.contract_price), f"contract {c.contract_id} ${float(c.contract_price):.2f} ({c.start_date} to {c.end_date or 'open'})", "contract"
        p = P[sku]
        ldate, note = dd, ""
        for ex in APPROVED:
            if ex["type"] == "price_freeze" and C[cid]["group_name"] == ex["group"] and ex["start"] <= dd <= ex["end"]:
                ldate, note = ex["list_date"], f" [Sep 13 prices kept per Dana's email {ex['msg']}]"
        new = ldate >= p["list_price_from"] or p["previous_list_price"] == ""
        lp = p["list_price"] if new else p["previous_list_price"]
        cu = C[cid]
        tier = cu["price_tier"] if (dd >= cu["tier_effective_from"] or cu["previous_tier"] == "") else cu["previous_tier"]
        up = money(Decimal(lp) * (1 - Decimal(str(TIER[tier]))))
        why = f"list ${float(lp):.2f} ({'from ' + p['list_price_from'] if new else 'before ' + p['list_price_from']}) less tier {tier} {int(TIER[tier]*100)}%" + note
        return up, why, ("freeze" if note else "tier")

    def taxable(cid, sku, dd):
        if sku == "DEL-FEE" or P.get(sku, {}).get("taxable") != "Y":
            return False
        cu = C[cid]
        if cu["tax_exempt"] == "Y" and (cu["exempt_cert_expires"] == "" or dd <= cu["exempt_cert_expires"]):
            return False
        return True

    def free_delivery(cid, dd):
        for ex in APPROVED:
            if ex["type"] == "fee_waiver" and ex["customer_id"] == cid and ex["start"] <= dd <= ex["end"]:
                return True, f"Dana waived the fee {ex['start']} to {ex['end']} by email ({ex['msg']})"
        cu = C[cid]
        if cu["free_delivery_from"] and cu["free_delivery_from"] <= dd and (cu["free_delivery_to"] == "" or dd <= cu["free_delivery_to"]):
            return True, f"free delivery {cu['free_delivery_from']} to {cu['free_delivery_to'] or 'open'}"
        return False, ""

    inv = inv.copy()
    inv["did"] = inv.memo.str.extract(r"(D-\d{6}-\d{4})")[0].fillna("")
    inv["so"] = inv.memo.str.extract(r"(SO-\d+)")[0].fillna("")
    invs = inv[inv.transaction_type == "Invoice"].copy()
    cms = inv[inv.transaction_type == "Credit Memo"].copy()
    asof = asof or max(invs.date.max(), dl.delivery_date.max())

    # ---- expected billing per delivery
    D = {}
    for did, grp in dl.groupby("delivery_id", sort=False):
        h = grp.iloc[0]
        D[did] = dict(did=did, cid=h.customer_id, date=h.delivery_date, so=h.order_id, typ=h.order_type,
                      status=",".join(sorted(set(grp.delivery_status))), lines=grp)

    # ---- map invoices to deliveries
    heads = invs.groupby("invoice_no", sort=False).agg(did=("did", "first"), so=("so", "first"), cust=("customer", "first"),
                                                        ship=("ship_date", "first"), date=("date", "first"), memo=("memo", "first")).reset_index()
    so2d = {v["so"]: k for k, v in D.items()}
    inv2d, d2inv = {}, {}
    for _, h in heads.iterrows():
        did = h.did or so2d.get(h.so, "")
        if did:
            inv2d[h.invoice_no] = (did, "memo" if h.did else "order no")
    claimed = {v[0] for v in inv2d.values()}
    for _, h in heads.iterrows():
        if h.invoice_no in inv2d:
            continue
        skus = set(invs[invs.invoice_no == h.invoice_no].item) - {"DEL-FEE"}
        cid = QB.get(h.cust)
        best = None
        for did, v in D.items():
            if did in claimed:
                continue
            if h.ship:
                if v["date"] != h.ship and v["date"] != h.date:
                    continue
            elif not (v["date"] <= h.date and (d(h.date) - d(v["date"])).days <= 10):
                continue
            ds = set(v["lines"].sku)
            sc = len(skus & ds) / max(1, len(skus | ds))
            if v["cid"] == cid:
                sc += 1
            if best is None or sc > best[0]:
                best = (sc, did)
        if best and best[0] >= 1.5:
            inv2d[h.invoice_no] = (best[1], "customer + date + items")
            claimed.add(best[1])
    for ino, (did, how) in inv2d.items():
        d2inv.setdefault(did, []).append(ino)

    rows = []  # each: dict(kind, keys..., amount, cause, evidence[list], detail)

    def ev(file, record, shows, expected=""):
        return dict(file=file, record=record, shows=shows, expected=expected)

    for did, v in D.items():
        cid, dd = v["cid"], v["date"]
        cname = C[cid]["quickbooks_name"]
        lines = v["lines"]
        nolines = f"{len(lines)} lines, {int(lines.qty_delivered.astype(int).sum())} cases delivered"
        billable = v["typ"] != "SAMPLE"
        exp = {}
        for _, ln in lines.iterrows():
            q = int(ln.qty_delivered)
            if q <= 0 or not billable or ln.delivery_status == "REFUSED":
                continue
            up, why, src = price(cid, ln.sku, dd)
            e = exp.setdefault(ln.sku, dict(qty=0, up=up, why=why, src=src, line=ln.line_no))
            e["qty"] += q
        sub = sum(rnd(e["up"] * e["qty"]) for e in exp.values())
        fd, fdwhy = free_delivery(cid, dd)
        fee = 35.0 if (exp and sub < 300 and not fd) else 0.0
        invnos = d2inv.get(did, [])
        dline = ev("delivery_log.csv", f"delivery {did}", f"{cname} ({cid}), delivered {dd}: {nolines}; type {v['typ']}, status {v['status']}")

        if not invnos:
            if not exp:
                continue
            deadline = add_bdays(d(dd), 3).isoformat()
            if deadline >= asof:
                continue
            # rule 5: last-days-of-month deliveries are often invoiced early next month; until that month's
            # invoices are loaded we can't call them missed (the October run decides them on real data)
            if dd[:7] == asof[:7] and dd[8:] >= "21" and asof[8:] >= "28":
                continue
            amt = rnd(sub + fee)
            rows.append(dict(kind="NOTINV", problem="Delivery never invoiced", delivery_id=did, amount=amt, date=dd, cid=cid,
                             cause="Deliveries never invoiced",
                             evidence=[ev("delivery_log.csv", f"delivery {did}", f"{cname}, delivered {dd}: {len(exp)} billable lines, ${sub:,.2f} at correct prices" + (f" + $35.00 delivery fee" if fee else ""), f"An invoice by {deadline}"),
                                       ev("invoices.csv", "all invoices", f"No invoice mentions {did} or order {v['so']}", "One invoice for this delivery")]))
            continue
        if len(invnos) > 1:
            invnos = sorted(invnos)
            for extra in invnos[1:]:
                L = invs[invs.invoice_no == extra]
                amt = -rnd(L.amount.astype(float).sum())
                rows.append(dict(kind="DUPINV", problem="Delivery invoiced twice", invoice_no=extra, amount=amt, date=dd, cid=cid,
                                 cause="Same delivery invoiced twice",
                                 evidence=[ev("invoices.csv", f"invoice {extra}", f"${-amt:,.2f} before tax, memo '{L.iloc[0].memo}'", "No second invoice"),
                                           ev("invoices.csv", f"invoice {invnos[0]}", f"Already bills delivery {did}"), dline]))
        ino = invnos[0]
        L = invs[invs.invoice_no == ino]
        h = L.iloc[0]
        icid = QB.get(h.customer)
        if not billable or (not exp and v["status"] == "REFUSED"):
            amt = -rnd(L.amount.astype(float).sum())
            why = "a free SAMPLE order" if not billable else "a REFUSED delivery"
            rows.append(dict(kind="SAMPLEBILLED", problem="Sample billed" if not billable else "Refused delivery billed", invoice_no=ino, amount=amt, date=dd, cid=cid,
                             cause="Free samples / refused deliveries billed",
                             evidence=[ev("invoices.csv", f"invoice {ino}", f"${-amt:,.2f} billed to {h.customer}", "$0.00, not invoiced"), dline]))
            continue
        if icid != cid:
            amt = 0.0
            rows.append(dict(kind="WRONGCUST", problem="Invoice addressed to wrong customer", invoice_no=ino, amount=rnd(L.amount.astype(float).sum()), date=dd, cid=cid,
                             cause="Invoices billed to the wrong customer",
                             evidence=[ev("invoices.csv", f"invoice {ino}", f"Billed to {h.customer} ({icid}), ${L.amount.astype(float).sum():,.2f}", f"Billed to {cname} ({cid})"), dline]))
        # credits that fix this invoice
        corr = cms[(cms.invoice_no == ino) & (cms.reason_code == "BILLING_CORRECTION")]
        corr_amt = corr.groupby("item").amount.apply(lambda s: s.astype(float).sum()).to_dict()
        corr_qty = corr.groupby("item").qty.apply(lambda s: s.astype(float).sum()).to_dict()
        # item lines
        for sku in sorted(set(L.item) | set(exp)):
            if sku == "DEL-FEE":
                continue
            bl = L[L.item == sku]
            e = exp.get(sku)
            billed_amt = rnd(bl.amount.astype(float).sum()) + rnd(corr_amt.get(sku, 0))
            billed_qty = bl.qty.astype(float).sum() + corr_qty.get(sku, 0)
            exp_amt = rnd(e["up"] * e["qty"]) if e else 0.0
            diff = rnd(exp_amt - billed_amt)
            if abs(diff) < 0.005:
                continue
            ev_rows = []
            for _, b in bl.iterrows():
                ev_rows.append(ev("invoices.csv", f"invoice {ino}, line {b.line_no}", f"rate ${float(b.rate):.2f} x {b.qty} cases = ${float(b.amount):,.2f}",
                                  f"${e['up']:.2f} x {e['qty']} cases" if e else "not billed"))
            for _, c in corr[corr.item == sku].iterrows():
                ev_rows.append(ev("invoices.csv", f"credit memo {c.credit_memo_no}", f"BILLING_CORRECTION {float(c.amount):,.2f}"))
            dlines = lines[lines.sku == sku]
            for _, dlr in dlines.iterrows():
                ev_rows.append(ev("delivery_log.csv", f"delivery {did}, line {dlr.line_no}", f"{sku}: ordered {dlr.qty_ordered}, shipped {dlr.qty_shipped}, delivered {dlr.qty_delivered} {('(' + dlr.short_reason + ')') if dlr.short_reason else ''} on {dd}"))
            if e:
                ev_rows.append(ev("products.csv" if e["src"] == "tier" else ("contract_prices.csv" if e["src"] == "contract" else "inbox.csv"), sku, e["why"], f"${e['up']:.2f} a case"))
            if not e:
                kind, problem = "NOTDELIV", "Billed for item not delivered"
            elif len(bl) == 0:
                kind, problem = "LINEMISSING", "Delivered item missing from invoice"
            elif len(bl) > 1 and billed_qty > e["qty"]:
                kind, problem = "DUPLINE", "Line billed twice"
            elif billed_qty > e["qty"]:
                kind, problem = "OVERQTY", "Billed more cases than delivered"
            elif billed_qty < e["qty"]:
                kind, problem = "UNDERQTY", "Billed fewer cases than delivered"
            else:
                rates = set(bl.rate.astype(float))
                kind, problem = "PRICE", "Wrong price"
                br = list(rates)[0]
                p = P[sku]
                if e["src"] == "tier" and p["previous_list_price"] and dd >= p["list_price_from"]:
                    cu = C[cid]
                    tier = cu["price_tier"]
                    old = money(Decimal(p["previous_list_price"]) * (1 - Decimal(str(TIER[tier]))))
                    if abs(br - old) < 0.005:
                        kind, problem = "OLDPRICE", "Old price after increase"
                if kind == "PRICE":
                    # contract expired but still used?
                    for c in CON.get((cid, sku), []):
                        if abs(br - float(c.contract_price)) < 0.005 and not (c.start_date <= dd and (c.end_date == "" or dd <= c.end_date)):
                            kind, problem = ("EXPIREDCON", "Expired contract price used") if c.end_date and dd > c.end_date else ("EARLYCON", "Contract price used before it started")
                    if e["src"] == "contract" and kind == "PRICE":
                        kind, problem = "CONTRACTMISSED", "Contract price not applied"
                    if kind == "PRICE" and e["src"] == "tier":
                        cu = C[cid]
                        for t, disc in TIER.items():
                            lp = p["list_price"] if dd >= p["list_price_from"] or not p["previous_list_price"] else p["previous_list_price"]
                            if abs(br - money(Decimal(lp) * (1 - Decimal(str(disc))))) < 0.005:
                                kind, problem = "WRONGTIER", f"Billed at tier {t} instead of tier {cu['price_tier'] if dd >= cu['tier_effective_from'] or not cu['previous_tier'] else cu['previous_tier']}"
                                break
                    if kind == "PRICE" and e["src"] == "exception":
                        kind, problem = "EXCEPTIONMISSED", "Email-approved price not applied"
            rows.append(dict(kind=kind, problem=problem, invoice_no=ino, sku=sku, amount=diff, date=dd, cid=cid, evidence=ev_rows + [dline],
                             billed_rate=(float(bl.rate.iloc[0]) if len(bl) else None), exp_rate=(e["up"] if e else None)))
        # delivery fee
        fl = L[L.item == "DEL-FEE"]
        billed_fee = rnd(fl.amount.astype(float).sum()) + rnd(corr_amt.get("DEL-FEE", 0))
        if abs(billed_fee - fee) > 0.005:
            if len(fl) > 1:
                kind, problem = "FEETWICE", "Delivery fee billed twice"
            elif fee == 0 and fd:
                kind, problem = "FEEFREE", "Delivery fee during free-delivery period"
            elif fee == 0:
                kind, problem = "FEEOVER300", "Delivery fee on order of $300 or more"
            else:
                kind, problem = "FEEMISSING", "Delivery fee not charged"
            rows.append(dict(kind=kind, problem=problem, invoice_no=ino, sku="DEL-FEE", amount=rnd(fee - billed_fee), date=dd, cid=cid,
                             evidence=[ev("invoices.csv", f"invoice {ino}", f"{len(fl)} DEL-FEE line(s), ${billed_fee:.2f}", f"${fee:.2f}"),
                                       ev("delivery_log.csv", f"delivery {did}", f"merchandise ${sub:,.2f} at correct prices on {dd}", "fee only under $300.00"),
                                       ev("customers.csv", cid, fdwhy or f"no free delivery on {dd}")]))
        # tax
        tdiff = 0.0; tlines = []
        for _, b in L.iterrows():
            if b["item"] == "DEL-FEE":
                exp_tax = 0.0
            else:
                exp_tax = money(Decimal(b.amount) * Decimal("0.08875")) if taxable(cid, b["item"], dd) else 0.0
            bt = float(b.line_tax or 0)
            if abs(bt - exp_tax) > 0.015:
                # product set up without tax in QuickBooks: a line-level problem
                if C[cid]["tax_exempt"] != "Y" and b.taxable != P.get(b["item"], {}).get("taxable"):
                    rows.append(dict(kind="TAXSETUP", problem="Taxable item billed without sales tax" if exp_tax > bt else "Sales tax on non-taxable item",
                                     invoice_no=ino, sku=b["item"], amount=rnd(exp_tax - bt), date=dd, cid=cid,
                                     evidence=[ev("invoices.csv", f"invoice {ino}, line {b.line_no}", f"{b['item']} ${float(b.amount):,.2f}, taxable {b.taxable}, tax ${bt:.2f}", f"tax ${exp_tax:.2f}"),
                                               ev("products.csv", b["item"], f"taxable = {P.get(b['item'], {}).get('taxable')}", "8.875% sales tax" if exp_tax > bt else "no tax"),
                                               dline]))
                else:
                    tdiff += exp_tax - bt; tlines.append((b, exp_tax))
        if tlines and abs(tdiff) > 0.005:
            cu = C[cid]
            kind = "TAXEXEMPT" if tdiff < 0 and cu["tax_exempt"] == "Y" else ("TAXEXPIRED" if cu["tax_exempt"] == "Y" else "TAX")
            problem = {"TAXEXEMPT": "Sales tax charged to exempt customer", "TAXEXPIRED": "No tax after exemption expired", "TAX": "Sales tax wrong"}[kind]
            rows.append(dict(kind=kind, problem=problem, invoice_no=ino, amount=rnd(tdiff), date=dd, cid=cid,
                             evidence=[ev("invoices.csv", f"invoice {ino}, line {b.line_no}", f"{b["item"]} tax ${float(b.line_tax or 0):.2f}", f"${t:.2f}") for b, t in tlines[:4]] +
                                      [ev("customers.csv", cid, f"tax_exempt {cu['tax_exempt']}, certificate expires {cu['exempt_cert_expires'] or 'n/a'}"), dline]))
    return rows, dict(inv2d=inv2d, D=D, C=C, QB=QB, asof=asof, price=price, CON=CON, P=P)

if __name__ == "__main__":
    import collections
    g = load()
    rows, ctx = run(g)
    cnt = collections.Counter((x["kind"]) for x in rows)
    tot = collections.defaultdict(float)
    for x in rows:
        tot[x["kind"]] += x["amount"]
    for k, n in cnt.most_common():
        print(f"{k:16} {n:5} {tot[k]:12,.2f}")
    print("matched invoices", len(ctx["inv2d"]))
