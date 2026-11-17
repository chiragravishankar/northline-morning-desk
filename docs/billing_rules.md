# Northline Supply — business rules

These are Northline's own rules. They decide what "correct" means. Money is in US dollars.
Business days are Monday to Friday, except Labor Day (Mon Sep 7, 2026).

## 1. What a customer pays per case

The price depends on the **delivery date**, not the invoice date. Use the first rule that applies:

1. **Contract price.** If `contract_prices.csv` has a contract for that customer and SKU that is active on the delivery date, the price is the contract price. A contract is active from `start_date` to `end_date`, inclusive. A blank `end_date` means it has no end.
2. **Tier discount.** Otherwise, take the list price in effect on the delivery date and subtract the customer's tier discount. In `products.csv`, `list_price` applies from `list_price_from`; deliveries before that date use `previous_list_price`.

| Tier | Discount |
|---|---|
| A | 10% |
| B | 6% |
| C | 3% |
| D | 0% (list price) |

If a customer's tier changed, `customers.csv` shows the current tier, the date it started (`tier_effective_from`), and the tier before that (`previous_tier`). Deliveries before that date use the previous tier.

Round the unit price to the cent (half up). Line amount = unit price × cases.

## 2. Quantities

- Bill what was **delivered** (`qty_delivered`), not what was ordered or shipped.
- Lines with 0 delivered are not billed.
- Credit memos are rows in `invoices.csv` with `transaction_type = Credit Memo`. Their `invoice_no` is the invoice they credit, and their quantities and amounts are negative.
- Credit memos with reason `BILLING_CORRECTION` fix the invoice they credit. Count them when you check that invoice.
- `DAMAGED_GOODS` credits are goodwill. They do not change what should have been billed.

## 3. Delivery fee

- Charge **$35.00** per delivery (item `DEL-FEE`, one line) when the delivery's merchandise subtotal is **under $300.00**. Compute the subtotal with the correct prices and delivered quantities.
- No fee when the delivery date falls in the customer's free-delivery period (`free_delivery_from` to `free_delivery_to` in `customers.csv`; a blank `free_delivery_to` means no end).
- At most one fee per delivery. The fee is not taxed.

## 4. Sales tax

- **8.875%** on items marked `taxable = Y` in `products.csv`. Compute it per line and round to the cent.
- No tax for a tax-exempt customer (`tax_exempt = Y`), but only for deliveries on or before `exempt_cert_expires`. After that date, charge tax.

## 5. Invoicing

- Each delivery gets one invoice. The clerk usually notes the delivery ID (for example `D-260914-0123`) in the invoice `memo`.
- Address the invoice to the customer who received the delivery. Match `customer` on the invoice to `quickbooks_name` in `customers.csv`.
- Invoice within **3 business days** after delivery. A delivery with no invoice yet counts as missed only after those 3 business days have passed. Deliveries in the last days of a month are often invoiced early the next month.
- `SAMPLE` orders and `REFUSED` deliveries are not invoiced.

## 6. Customer email

- Every customer question or request needs a reply by the **end of the next business day**.
- A message that only says thanks does not need a reply.
- When we promise a credit by email, the credit memo must be issued within **5 business days**.

## 7. Paying suppliers

- **Price.** Pay the unit cost on our purchase order (`unit_cost` in `purchase_orders.csv`). The PO price holds even if the supplier raises prices later. Suppliers announce increases by email, and POs placed after an increase carry the new cost.
- **Quantity.** Pay only for the cases we accepted (`qty_accepted` in `purchase_orders.csv`). Damaged cases are refused at the dock. A PO line can arrive in more than one shipment: each shipment is its own row, and each is billed separately.
- **Freight.** It depends on the supplier's `freight_terms`:
  - `ALWAYS_PREPAID`: never pay freight.
  - `PREPAID_OVER`: pay freight only when the PO total is under `free_freight_min`.
  - `COLLECT`: freight is allowed.
- **Matching.** The AP clerk types the PO number into `po_ref` by hand. Bill lines name items by `supplier_item_code`, which is also on the PO line. Enter each supplier invoice only once.
- **Bank details.** Pay only into the account in `suppliers.csv` (`bank_account_last4`). A bank change that arrives by email must be checked by calling the supplier at the phone number on file.

## 8. Exceptions approved by email

Dana sometimes approves an exception by email: a price, a fee or a contract term. An exception she approves in writing applies for the customers and dates she gives, even if nobody updated QuickBooks or the master files. A request that Dana did not approve doesn't count.
