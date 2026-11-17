# Your two output files: `findings.csv` and `evidence.csv`

Your code reads the Northline data and writes two files. Both feed your Base44 app, and you submit one of them.

```
data/*.csv ─► your code ─┬─► findings.csv ─┬─► submit it (scored)
                         │                 └─► Base44: Findings table   (Dana's queue)
                         └─► evidence.csv ───► Base44: Evidence table   (the proof)
                                               Base44: Decisions table  (made in the app)
```

| File | One row per | Submit it? | In Base44 |
|---|---|---|---|
| `findings.csv` | problem | **Yes**, on the event site, by 7:30 PM | The **Findings** table: Dana's queue |
| `evidence.csv` | record that proves a problem | No | The **Evidence** table: what Dana sees when she opens a finding |

Blank templates and filled-in examples are in `templates/`, and the blank `findings.csv` is also on the event site. The examples use made-up IDs.

## `findings.csv`: one row per problem

Each row answers three questions. Only these are needed for your score:

| Question | Columns | Example |
|---|---|---|
| **What** is wrong? | `problem`: a few words | `Old price after increase` |
| **Where** is it? | the record IDs: `delivery_id`, `invoice_no`, `sku`, `po_no`, `bill_id`, `supplier`, `message_id`. Fill in only the ones that point to the problem (table below). | `1099901` and `NL-99001` |
| **How much?** | `amount`: dollars, before sales tax | `7.52` |

**Which record IDs to fill in.** Leave the others blank.

| The problem is about… | Fill in | Example |
|---|---|---|
| a delivery as a whole | `delivery_id` | `D-260915-9991` |
| a whole invoice | `invoice_no` | `1099905` |
| one line on an invoice | `invoice_no` + `sku` | `1099901`, `NL-99001` |
| one line on a supplier bill | `bill_id` + `sku` (or `po_no` + `sku`) | `B-69901`, `NL-99002` |
| a whole supplier bill | `bill_id` | `B-69901` |
| a supplier as a whole | `supplier` | `SUP-199` |
| an email | `message_id` | `M-999901` |

For a delivery fee, write `DEL-FEE` as the SKU. For freight, write `FREIGHT`.

**Amount.**
- **Positive:** money Northline should still collect or recover.
- **Negative:** money Northline owes back to a customer.
- **Before sales tax.** For a sales-tax problem, the amount is the tax itself.
- **No money involved** (an unanswered email): `0`.

**One row per record.** If one cause hits 30 invoice lines, write 30 rows.

**Columns for your app (optional, not scored).** These make the Base44 app work better:

| Column | What to put | Why |
|---|---|---|
| `month` | `september` or `october` | The app shows totals by month, and judges compare them with your file. |
| `cause` | The one cause behind the row, e.g. `NL-99001 still at its pre-Sep 14 price` | Rows with the same cause are grouped in Dana's queue. |
| `finding_id` | An ID built from the problem and its records, e.g. `OLDPRICE-1099901-NL-99001` | A re-run gives the same IDs, so Dana's decisions carry over at 7 PM. |

You can add any other columns you like (customer, explanation…). We ignore them for scoring, and column order doesn't matter.

**Check before you submit.** When you pick a file on the event site, it tells you how many rows it can read and which rows have no record ID. That check is free: it doesn't use up a submission.

## `evidence.csv`: the records behind each finding

Each finding gets one or more rows, one per record that proves it. This is what the app shows when Dana opens a finding.

| Column | What to put | Example |
|---|---|---|
| `finding_id` | The finding this record proves | `OLDPRICE-1099901-NL-99001` |
| `file` | The data file it comes from | `invoices.csv` |
| `record` | Which row, in words | `invoice 1099901, line 2` |
| `shows` | What that row says | `rate $43.24 × 4 cases` |
| `expected` | What the rules say it should be (blank if this row is just context) | `$45.12 a case` |

A good finding usually has 2–4 evidence rows. For example, a price problem has the invoice line, the product's list price, the customer's tier and the delivery line.

## How the files feed your Base44 app

Make three tables in Base44:

| Table | Comes from | Holds |
|---|---|---|
| **Findings** | import `findings.csv` | one row per problem |
| **Evidence** | import `evidence.csv` | the records behind each finding, linked by `finding_id` |
| **Decisions** | made in the app | `finding_id`, status (new / approved / dismissed), reason, the draft (invoice, credit, reply, dispute or hold), who decided and when |

- **Queue:** the Findings table, grouped by `cause`, biggest total first. A finding with no Decision is new.
- **Proof:** the Evidence rows for the finding that's open.
- **Totals:** the sum of `amount` by month. Because the app loads the same file you submit, its totals match your submission. Judges check this.

## At 7 PM: October

1. Add October's files to September's (see `OCTOBER.md` in the drop), then re-run your code on both months. It writes new `findings.csv` and `evidence.csv` covering September **and** October.
2. In Base44, clear the Findings and Evidence tables, then import the new files. Base44 imports only add rows; they never replace them.
3. Leave the Decisions table alone. If your `finding_id`s are built from the records, Dana's approvals carry over.
4. Show **what changed**. If you fill in `month` and `cause`: a cause with only October rows is **new**, one with rows in both months is **still open**, and one with only September rows is **fixed**.

## How we score `findings.csv`

- We match each row to our answer key by its record IDs. The wording in `problem` and any other columns doesn't affect the Catch score, but judges read it.
- A matched row earns credit. It earns full dollar credit when the amount is right.
- Listing the same problem twice earns nothing extra.
- Some things look wrong but are correct under `billing_rules.md`. Flagging them costs points.
- Submit on the event site as often as every 10 minutes. You see your Catch score each time, and the live board shows everyone's. Your latest file counts, so the final one should cover both months.
