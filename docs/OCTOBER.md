# October data (released at 7:00 PM)

This is Northline's data at the end of **Friday, Oct 30, 2026**. Move this `october` folder into your kit's `data/` folder, next to `september`.

## How to combine it with September

| Files | What to do | Why |
|---|---|---|
| `delivery_log.csv`, `invoices.csv`, `purchase_orders.csv`, `supplier_bills.csv`, `inbox.csv` | **Add** them to September's | They hold October activity only. Some September deliveries are invoiced in October, and some September POs arrive and are billed in October. |
| `customers.csv`, `contract_prices.csv`, `products.csv`, `suppliers.csv` | **Replace** September's | They show the state at Oct 30. Tiers, contracts, prices and tax exemptions may have changed. |

Columns are the same as in September.

## Dana's new request

> "Every Monday at 8, Frank (the owner) asks me three things: how much did we get back last week, how much is still at risk, and what does he need to decide. Can your app write that note for me?"

Add this to your Base44 app. It counts toward Product sense.

## Then

1. Re-run your code on both months. It writes new `findings.csv` and `evidence.csv` covering September **and** October.
2. In Base44, clear the Findings and Evidence tables, then import the new files. Keep the Decisions table.
3. Show Dana what's new, what's still open and what got fixed, and build her Monday note.
4. Submit the new `findings.csv` on the event site by 7:30 PM.

`FINDINGS_AND_EVIDENCE.md` in your kit explains each step.
