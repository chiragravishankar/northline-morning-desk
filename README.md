# Northline Morning Desk

Team Red's entry for **Nothing Slips Through** (Peri · NYU PMC Buildathon × Base44, Nov 16 2026).

Northline Supply runs on five systems that don't talk to each other: the delivery log, QuickBooks, prices & contracts, purchasing and a shared inbox. This repo holds the code that reads all five, applies `docs/billing_rules.md`, and writes the two files that feed Dana's Base44 app.

- **App:** https://northline-morning-desk-604a40a8.base44.app
- **Final submission:** `output/findings.csv` (833 rows, September $89,685.82 + October $73,619.87)

```
data/september + data/october ─► engine/run.py ─┬─► output/findings.csv ─► Base44 Finding table (and the scored submission)
                                                └─► output/evidence.csv ─► Base44 Evidence table (proof, documents, audit, ops)
```

## Run it

```bash
pip install pandas
./run_october.sh          # September + October (adds October transactions, replaces master files)
cd engine && python3 run.py ../data/september ../output_sep   # September only
```

Every number comes from code. Base44's AI only writes wording (drafts, the Monday note).

## What the engine checks

| Area | Check | Rule |
|---|---|---|
| Customer billing (`billing.py`) | Delivery never invoiced (after 3 business days) | 5 |
| | Delivery invoiced twice · invoice addressed to the wrong customer · samples/refused deliveries billed | 5 |
| | Price: contract → list price on the delivery date → tier (with tier history), half-up rounding | 1 |
| | Old price after a price change · wrong tier · expired / missing contract · email-approved price not applied | 1, 8 |
| | Billed more / fewer cases than delivered · item billed but not delivered · delivered item left off | 2 |
| | Delivery fee: missing under $300, charged at $300+, charged during free delivery, charged twice | 3 |
| | Sales tax: item set up without tax, tax on exempt customers, exemption expired | 4 |
| Supplier bills (`ap.py`) | Billed above PO price (respecting announced supplier increases) · billed for cases not accepted at the dock | 7 |
| | Freight against prepaid terms · duplicate supplier invoices · payment to an account not on file | 7 |
| | Mistyped / blank PO refs repaired from item codes; supplier code changes matched by description | 7 |
| Inbox (`inbox.py`) | Customer email with no reply by end of next business day (thank-you notes skipped) | 6 |
| | Credit promised by email but no credit memo within 5 business days | 6 |
| | Fake bank-change email (sender domain ≠ supplier's) | 7 |

**Dana's email exceptions** (`exceptions.py`): Kettle & Crumb keep Sep 13 prices through Oct 31, Copper Biryani's fee waived Sep 21–Oct 16, Bagel Kitchen price match from Oct 1. Brick Lane's request was **refused**, so new prices apply.

## Beyond the scored file (evidence.csv sections)

| Section | What | Used by |
|---|---|---|
| `proof` | The records behind each finding (record, shows, expected) | Finding proof |
| `header`, `line` | Every flagged transaction as an ERP record: header fields, invoice / delivery note / credit memo lines, bill / PO / dock-receipt lines, and the **price basis** per line (contract, price list, tier, PO cost) | Transaction page |
| `audit` | Who touched each transaction and when (created by, driver, signer, buyer, receiver, AP clerk, emails) | Audit trail |
| `match` | Three-way match per PO: PO amount vs accepted vs billed across all bills | Payables › Three-way match |
| `ops`, `flow` | Fulfillment and inbound exceptions from the delivery log and dock, stock in/out per SKU | Operations |

Each transaction gets a stable Northline reference (`NL-INV-…`, `NL-BILL-…`, `NL-DEL-…`, `NL-MSG-…`) built from its source record, so IDs and Dana's decisions survive a re-run.

## Repo layout

```
engine/      detection code (run.py is the entry point)
data/        September and October drops as released
output/      findings.csv + evidence.csv (both months), findings_september_only.csv
docs/        the case brief, billing rules, data dictionary, file spec, October notes
```

## Team

- Chirag Ravishankar ([@chiragravishankar](https://github.com/chiragravishankar))
- Ritu Kumar ([@rituskumar2601](https://github.com/rituskumar2601))
