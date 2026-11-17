# Data dictionary

Nine files describe one month of Northline. September is in `data/september/`. October arrives at 7 PM with the same files and columns.
Money is in US dollars, and dates are `YYYY-MM-DD`. Read `billing_rules.md` for what "correct" means.

| Kind | File | What it holds | Rows (Sep / Oct) |
|---|---|---|---|
| Master data | `customers.csv` | Customer accounts: QuickBooks name, price tier and tier history, tax exemption, free delivery, delivery days | 136 / 140 |
| Master data | `contract_prices.csv` | Fixed prices per customer and SKU, with start and end dates | 163 / 164 |
| Master data | `products.csv` | Our SKUs: category, taxable flag, supplier and supplier item code, list price (current and previous) | 420 / 423 |
| Master data | `suppliers.csv` | Supplier accounts: freight terms, payment terms, the bank account on file | 48 / 48 |
| Transactions | `delivery_log.csv` | Every delivery line: ordered, shipped and delivered quantities, proof of delivery | 5,144 / 5,396 |
| Transactions | `invoices.csv` | QuickBooks invoice lines and credit memo lines | 4,961 / 5,392 |
| Transactions | `purchase_orders.csv` | Every PO line we sent to a supplier, and what arrived at the dock (one row per shipment) | 1,644 / 1,826 |
| Transactions | `supplier_bills.csv` | Supplier bills entered in QuickBooks, line by line | 1,245 / 1,579 |
| Transactions | `inbox.csv` | The shared inbox: orders@, ap@, and the ops manager's mail | 965 / 917 |

When October arrives, **add** its transaction files to September's and **replace** the master files. See `OCTOBER.md` in the drop.

## How the files connect

| From | To | How |
|---|---|---|
| `invoices.memo` | `delivery_log.delivery_id` | The memo usually mentions the delivery ID |
| `invoices.customer` | `customers.quickbooks_name` | Exact name |
| `invoices.invoice_no` on a credit memo row | `invoices.invoice_no` on invoice rows | The invoice it credits |
| `delivery_log.customer_id` | `customers.customer_id` | |
| `invoices.item`, `delivery_log.sku` | `products.sku` | `DEL-FEE` is the delivery fee |
| `contract_prices.customer_id` + `sku` | `customers`, `products` | |
| `supplier_bills.po_ref` | `purchase_orders.po_no` | |
| `supplier_bills.supplier_item_code` | `purchase_orders.supplier_item_code`, `products.supplier_item_code` | |
| `supplier_bills.vendor` | `suppliers.quickbooks_vendor_name` | |
| `inbox.thread_id` | `inbox.thread_id` | A conversation; `in_reply_to` points to the earlier message |

## `customers.csv`

| Column | Example | Notes |
|---|---|---|
| `customer_id` | C-1136 | Northline's customer ID; the delivery log uses it |
| `customer_name` | Queens Hope Charter School |  |
| `quickbooks_name` | Queens Hope Charter School | The customer name on QuickBooks invoices and credit memos (`customer`) |
| `group_name` | Brick Lane Cafés | Restaurant group, if the customer is one location of a group |
| `customer_type` | School |  |
| `borough` | Jersey City |  |
| `neighborhood` | Downtown JC |  |
| `ship_to_address` | 26 W 61st St |  |
| `zip` | 07302 |  |
| `contact_name` | Elena Zamora |  |
| `contact_email` | elena.zamora@queenshopecharters.com |  |
| `ap_email` | ap@queenshopecharters.com |  |
| `phone` | (347) 555-3944 |  |
| `payment_terms` | Net 30 | Days to pay |
| `price_tier` | B | Current tier: A 10%, B 6%, C 3%, D 0% off list |
| `tier_effective_from` | 2024-01-01 | Date the current tier started |
| `previous_tier` | A | Tier before that date (blank if it never changed) |
| `tax_exempt` | Y | Y = exempt from sales tax (while the certificate is valid) |
| `exempt_cert_no` | ST-119-657975 |  |
| `exempt_cert_expires` | 2027-06-30 | Last day the tax-exemption certificate is valid |
| `free_delivery_from` | 2026-06-01 | First day of free delivery (blank = none) |
| `free_delivery_to` |  | Last day of free delivery (blank = no end) |
| `delivery_days` | Thu | Scheduled delivery days |
| `route` | R5B |  |
| `sales_rep` | Nina Patel |  |
| `credit_limit` | 15000 |  |
| `account_opened` | 2021-01-27 |  |
| `status` | Active | Status in QuickBooks |

## `contract_prices.csv`

| Column | Example | Notes |
|---|---|---|
| `contract_id` | CT-3001 | Contract ID |
| `customer_id` | C-1089 | Northline's customer ID; the delivery log uses it |
| `customer_name` | Cedar Lantern Coffee |  |
| `sku` | NL-11008 | Northline's item number |
| `item_description` | Gotham Pro T-Shirt Bag 1/8 Thank You |  |
| `contract_price` | 29.19 | Fixed price per case for this customer and SKU (USD) |
| `start_date` | 2025-04-07 | First day the contract applies |
| `end_date` | 2026-12-31 | Last day (blank = no end) |
| `signed_on` | 2025-03-30 |  |
| `approved_by` | Carlos Vega |  |
| `notes` | One-year contract, not renewed | Free text |

## `products.csv`

| Column | Example | Notes |
|---|---|---|
| `sku` | NL-10007 | Northline's item number |
| `description` | Gotham Pro Kraft Takeout Box #1 | Supplier's or our item description |
| `category` | Takeout & Disposables |  |
| `subcategory` | Containers |  |
| `brand` | Gotham Pro |  |
| `pack` | 200/cs |  |
| `uom` | CS | Unit: CS (case) or EA (each) |
| `supplier_id` | SUP-101 | Northline's supplier ID |
| `supplier_item_code` | HU61358 | The supplier's item number; supplier bills use it |
| `list_price` | 47.49 | List price per case (USD), from `list_price_from` |
| `list_price_from` | 2026-01-05 | First day `list_price` applies |
| `price_change_id` | PC-2601 | Price change batch, e.g. PC-2609 |
| `previous_list_price` | 45.59 | List price before `list_price_from` (blank = none) |
| `standard_cost` | 27.74 | Current supplier cost per case (USD); bills are checked against the PO, not this |
| `taxable` | N | Y = sales tax applies (8.875%) |
| `status` | Active | Status in QuickBooks |
| `introduced_on` | 2022-01-01 |  |
| `case_weight_lb` | 6.6 |  |
| `case_cube_ft3` | 2.75 |  |
| `min_order_qty` | 1 |  |
| `storage_zone` | A-05 |  |
| `upc` | 094836680864 |  |

## `suppliers.csv`

| Column | Example | Notes |
|---|---|---|
| `supplier_id` | SUP-101 | Northline's supplier ID |
| `supplier_name` | Hudson Paper Co. |  |
| `quickbooks_vendor_name` | Hudson Paper | The supplier name on QuickBooks bills (`vendor`) |
| `category` | Disposables |  |
| `contact_name` | Hiro Ueda |  |
| `contact_title` | Customer Service Lead |  |
| `orders_email` | orders@hudsonpaper.com |  |
| `billing_email` | ar@hudsonpaper.com |  |
| `phone` | (516) 555-2681 |  |
| `address` | 915 Commerce Dr |  |
| `city` | Bethpage |  |
| `state` | NJ |  |
| `payment_terms` | Net 45 | Days to pay |
| `freight_terms` | PREPAID_OVER | ALWAYS_PREPAID, PREPAID_OVER (free over `free_freight_min`) or COLLECT |
| `free_freight_min` | 2000 | PO total (USD) at or above which freight is free |
| `remit_method` | ACH |  |
| `bank_name` | Provident |  |
| `bank_account_last4` | 8226 | The bank account on file; pay only into this one |
| `bank_verified_on` | 2025-04-01 |  |
| `lead_time_days` | 5 |  |
| `min_order_usd` | 250 |  |
| `w9_on_file` | Y |  |
| `vendor_since` | 2013-05-01 |  |
| `status` | Active | Status in QuickBooks |

## `delivery_log.csv`

| Column | Example | Notes |
|---|---|---|
| `delivery_id` | D-260901-0001 | Delivery ID; invoices usually mention it in `memo` |
| `order_id` | SO-48001 | Customer order number |
| `order_type` | STANDARD | STANDARD, RUSH or SAMPLE (samples are free) |
| `order_channel` | Phone |  |
| `order_date` | 2026-08-31 |  |
| `delivery_date` | 2026-09-01 | Date delivered; prices follow this date |
| `route_id` | R2C |  |
| `stop_no` | 1 |  |
| `truck_id` | TRK-19 |  |
| `driver` | R. Santos |  |
| `customer_id` | C-1078 | Northline's customer ID; the delivery log uses it |
| `ship_to_name` | Biryani Mango Coffee |  |
| `ship_to_address` | 307 W 72nd St |  |
| `zip` | 11237 |  |
| `line_no` | 1 | Line number within the document |
| `sku` | NL-10329 | Northline's item number |
| `item_description` | HarborPak Portion Cup 2 oz |  |
| `uom` | CS | Unit: CS (case) or EA (each) |
| `pack` | 2000/cs |  |
| `qty_ordered` | 7 | Cases ordered (on a PO) or cases the customer ordered (deliveries) |
| `qty_shipped` | 7 | Cases put on the truck |
| `qty_delivered` | 7 | Cases the customer accepted; bill these |
| `short_reason` | Out of stock | Why fewer cases arrived |
| `delivery_status` | DELIVERED | DELIVERED, PARTIAL or REFUSED |
| `signed_by` | Wen O. |  |
| `pod_time` | 12:29 |  |
| `delivery_notes` | Loading dock B |  |

## `invoices.csv`

| Column | Example | Notes |
|---|---|---|
| `transaction_type` | Invoice | `Invoice` or `Credit Memo` |
| `invoice_no` | 1048101 | QuickBooks invoice number. On a credit memo row: the invoice it credits |
| `credit_memo_no` | CM-5101 | Credit memo number (credit memo rows only) |
| `date` | 2026-09-01 | Invoice or credit memo date |
| `due_date` | 2026-10-01 | Payment due date |
| `terms` | Net 30 | Payment terms |
| `customer` | Biryani Mango Coffee | QuickBooks customer name; match to `customers.quickbooks_name` |
| `customer_email` | biryaniyilmaz12@gmail.com |  |
| `memo` | Ref D-260901-0001 - Williamsburg | Free text. On invoices it usually notes the delivery ID |
| `reason_code` | BILLING_CORRECTION | Credit memos: BILLING_CORRECTION (fixes the invoice) or DAMAGED_GOODS (goodwill) |
| `customer_po` | PO 5376 |  |
| `ship_date` | 2026-09-01 | Delivery date, as typed by the clerk (sometimes blank) |
| `sales_rep` | Nina Patel |  |
| `line_no` | 1 | Line number within the document |
| `item` | NL-10329 | SKU, or DEL-FEE for the delivery fee |
| `item_description` | HarborPak Portion Cup 2 oz |  |
| `class` | Takeout & Disposables |  |
| `qty` | 7 | Cases billed (negative on credit memos) |
| `rate` | 39.48 | Price per case billed (USD) |
| `amount` | 276.36 | qty × rate (USD; negative on credit memos) |
| `taxable` | N | Y = sales tax applies (8.875%) |
| `tax_rate` | 8.875% |  |
| `line_tax` | 0.00 | Sales tax on this line (USD) |
| `subtotal` | 1468.78 | Whole invoice or credit memo, before tax (USD) |
| `tax` | 42.67 | Whole invoice or credit memo, sales tax (USD) |
| `total` | 1511.45 | Whole invoice or credit memo, with tax (USD) |
| `status` | Paid | Status in QuickBooks |
| `balance` | 0.00 | Amount still unpaid (USD) |
| `created_by` | mike.tran |  |
| `created_at` | 2026-09-01 09:56 |  |

## `purchase_orders.csv`

| Column | Example | Notes |
|---|---|---|
| `po_no` | PO-26001 | Purchase order number |
| `po_date` | 2026-08-24 |  |
| `supplier_id` | SUP-101 | Northline's supplier ID |
| `supplier_name` | Hudson Paper Co. |  |
| `buyer` | Raj Mehta |  |
| `expected_date` | 2026-08-31 |  |
| `po_line` | 1 | Line number on the PO |
| `sku` | NL-10546 | Northline's item number |
| `supplier_item_code` | HU63425 | The supplier's item number; supplier bills use it |
| `item_description` | Northline Value Hot Cup 16 oz |  |
| `qty_ordered` | 8 | Cases ordered (on a PO) or cases the customer ordered (deliveries) |
| `unit_cost` | 61.23 | Cost per unit (USD) |
| `line_amount` | 489.84 | qty_ordered × unit_cost (USD) |
| `po_total` | 2684.36 | Whole PO total (USD); used for the freight rule |
| `receipt_id` | RCV-70001 | Dock receipt ID (blank = not received yet) |
| `received_date` | 2026-08-31 | Date the shipment arrived |
| `received_by` | Luis Ortiz |  |
| `carrier` | R+L |  |
| `qty_received` | 8 | Cases that arrived in this shipment |
| `qty_damaged` | 0 | Cases refused at the dock as damaged |
| `qty_accepted` | 8 | Cases kept; pay for these |
| `receiving_notes` | Backorder balance | e.g. Backorder balance, Refused damaged cases at dock, Not received yet |

## `supplier_bills.csv`

| Column | Example | Notes |
|---|---|---|
| `bill_id` | B-60101 | QuickBooks bill ID |
| `vendor` | Brightline Sanitation | Supplier name in QuickBooks; match to `suppliers.quickbooks_vendor_name` |
| `supplier_invoice_no` | BS-60428 | The supplier's own invoice number |
| `bill_date` | 2026-08-26 |  |
| `due_date` | 2026-09-25 | Payment due date |
| `terms` | Net 30 | Payment terms |
| `po_ref` | PO-26271 | The PO this bill is for, typed by the AP clerk |
| `line_no` | 1 | Line number within the document |
| `supplier_item_code` | BR61567 | The supplier's item number; supplier bills use it |
| `description` | KEYSTONE BLEACH SPLASHLESS 6X81 OZ | Supplier's or our item description |
| `qty` | 40 | Cases billed (negative on credit memos) |
| `uom` | CS | Unit: CS (case) or EA (each) |
| `unit_cost` | 29.85 | Cost per unit (USD) |
| `amount` | 1194.00 | qty × rate (USD; negative on credit memos) |
| `line_type` | ITEM | ITEM or FREIGHT |
| `bill_total` | 4404.68 | Whole bill total (USD) |
| `status` | Paid | Status in QuickBooks |
| `paid_date` | 2026-09-24 | When the bill was paid (blank if unpaid) |
| `scheduled_pay_date` | 2026-10-15 | Unpaid bills: when the payment will go out |
| `payment_method` | ACH |  |
| `remit_to_account_last4` | 5273 | Bank account the payment goes to |
| `entered_by` | dana.ruiz |  |
| `memo` |  | Free text. On invoices it usually notes the delivery ID |

## `inbox.csv`

| Column | Example | Notes |
|---|---|---|
| `message_id` | M-001673 | Email ID |
| `thread_id` | T-01015 | Conversation ID; replies share it |
| `sent_at` | 2026-08-31 01:54 | Date and time sent |
| `mailbox` | ap@ | Which inbox it landed in |
| `direction` | inbound | inbound, outbound or internal |
| `from_name` | Packaging Expo |  |
| `from_email` | info@packexpo-east.org |  |
| `to` | dana@northlinesupply.com |  |
| `cc` | ap@northlinesupply.com |  |
| `subject` | Register now for Pack Expo East |  |
| `body` | View this email in your browser. Register now for Pack Expo … | Email text |
| `attachments` | SO_660832.pdf |  |
| `in_reply_to` | M-000019 | The message this one answers |
