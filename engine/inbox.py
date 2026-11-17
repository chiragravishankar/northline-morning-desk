"""Inbox checks: unanswered customer emails, promised credits never issued, fake bank-change emails."""
from common import *

import os
LATE = os.environ.get("LATE", "0") == "1"
THANKS = re.compile(r"^\s*(thanks|thank you|great|perfect|got it)[\s,!.]*(thank you|thanks)?[\s\w,!.]{0,12}$", re.I)

def run(g, asof):
    ib, cu, inv, su = g["ib"], g["cust"], g["inv"], g["su"]
    ev = lambda file, record, shows, expected="": dict(file=file, record=record, shows=shows, expected=expected)
    rows = []
    ce = {}
    for _, c in cu.iterrows():
        ce[c.contact_email] = c; ce[c.ap_email] = c
    out = ib[ib.direction == "outbound"]
    for _, m in ib[(ib.direction == "inbound") & ib.from_email.isin(ce)].iterrows():
        if THANKS.match(m.body.strip()):
            continue
        deadline = add_bdays(d(m.sent_at), 1).isoformat()
        if deadline >= asof:
            continue  # still inside the reply window
        rep = out[(out.thread_id == m.thread_id) & (out.sent_at > m.sent_at)]
        c = ce[m.from_email]
        if not rep.empty:
            first = rep.sent_at.min()
            if LATE and first[:10] > deadline:
                rows.append(dict(kind="LATEREPLY", problem="Customer email answered late", message_id=m.message_id, amount=0.0, date=m.sent_at[:10], cid=c.customer_id,
                                 cause="Customer emails answered after the next business day",
                                 evidence=[ev("inbox.csv", f"message {m.message_id}", f"{c.customer_name}: '{m.subject}', {m.sent_at}", f"A reply by the end of {deadline}"),
                                           ev("inbox.csv", f"thread {m.thread_id}", f"First reply {first}")]))
            continue
        rows.append(dict(kind="NOREPLY", problem="Customer email with no reply", message_id=m.message_id, amount=0.0, date=m.sent_at[:10], cid=c.customer_id,
                         cause="Customer emails with no reply", customer=c.customer_name, subject=m.subject, body=m.body, from_email=m.from_email,
                         evidence=[ev("inbox.csv", f"message {m.message_id}", f"{c.customer_name}: '{m.subject}', {m.sent_at}", f"A reply by the end of {deadline}"),
                                   ev("inbox.csv", f"thread {m.thread_id}", "No later message from Northline in the thread")]))

    # credits promised by email
    cms = inv[inv.transaction_type == "Credit Memo"]
    for _, m in out[out.body.str.contains(r"issue a credit of \$", regex=True)].iterrows():
        amt = float(re.search(r"credit of \$([\d,]+\.\d\d)", m.body).group(1).replace(",", ""))
        ino = re.search(r"invoice #?(\d{7})", m.body).group(1)
        deadline = add_bdays(d(m.sent_at), 5).isoformat()
        got = cms[(cms.invoice_no == ino) & (cms.date <= deadline) & (cms.reason_code != "BILLING_CORRECTION")]
        got_any = cms[cms.invoice_no == ino]
        if not got.empty:
            issued = -got.amount.astype(float).sum()
            if abs(issued - amt) > 0.01:
                rows.append(dict(kind="CREDITSHORT", problem="Credit issued for a different amount than promised", message_id=m.message_id, amount=-rnd(amt - issued), date=m.sent_at[:10],
                                 cause="Credits issued for a different amount than promised",
                                 evidence=[ev("inbox.csv", f"message {m.message_id}", f"promised ${amt:,.2f} on invoice {ino}", f"${amt:,.2f}"),
                                           ev("invoices.csv", f"credit memo {', '.join(got.credit_memo_no)}", f"issued ${issued:,.2f}", f"${amt:,.2f}")]))
            continue
        if deadline >= asof and got_any.empty:
            continue
        inbound = ib[(ib.thread_id == m.thread_id) & (ib.direction == "inbound")]
        cust = inbound.iloc[0].from_email if len(inbound) else ""
        rows.append(dict(kind="CREDITPROMISED", problem="Promised credit never issued", message_id=m.message_id, invoice_no="", amount=-amt, date=m.sent_at[:10],
                         cause="Credits promised by email but never issued", promised_invoice=ino,
                         evidence=[ev("inbox.csv", f"message {m.message_id}", f"{m.from_name}, {m.sent_at}: promised a ${amt:,.2f} credit on invoice {ino}", f"Credit memo by {deadline}"),
                                   ev("invoices.csv", f"credit memos for invoice {ino}", "None issued" if got_any.empty else f"Issued late: {', '.join(got_any.credit_memo_no)} on {', '.join(got_any.date)}", f"${amt:,.2f} credit")]))

    # fake bank-detail changes: a bank change from a domain that is not the supplier's
    for _, m in ib[ib.subject.str.contains("bank", case=False) & (ib.direction == "inbound")].iterrows():
        dom = m.from_email.split("@")[-1]
        sup = None
        for _, s in su.iterrows():
            if s.supplier_name.split()[0].lower() in m.subject.lower() or s.quickbooks_vendor_name.lower() in m.body.lower():
                sup = s; break
        if sup is None:
            continue
        real = sup.billing_email.split("@")[-1]
        acct = re.search(r"ending:?\s*(\d{4})", m.body)
        if dom != real:
            rep = ib[(ib.thread_id == m.thread_id) & (ib.sent_at > m.sent_at)]
            rows.append(dict(kind="FAKEBANK", problem="Fake bank-change email", message_id=m.message_id, supplier=sup.supplier_id, amount=0.0, date=m.sent_at[:10],
                             cause=f"Fake bank-change email for {sup.quickbooks_vendor_name}",
                             evidence=[ev("inbox.csv", f"message {m.message_id}", f"From {m.from_email}: move payments to account ending {acct.group(1) if acct else '?'}", f"Sender domain {real}; call {sup.phone} to verify"),
                                       ev("suppliers.csv", sup.supplier_id, f"bank on file {sup.bank_name} ...{sup.bank_account_last4}, verified {sup.bank_verified_on}")] +
                                      [ev("inbox.csv", f"message {x.message_id}", f"{x.from_name}: '{x.body[:80]}'", "Call the supplier first") for _, x in rep.iterrows()]))
    return rows
