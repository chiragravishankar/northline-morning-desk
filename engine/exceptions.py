"""Exceptions Dana approved in writing (billing_rules.md section 8).
Each entry cites the email that approves it. Requests Dana refused are listed too, so we never apply them."""

APPROVED = [
    # Kettle & Crumb prepaid Q4: keep Sep 13 prices on everything through Oct 31, tier discount still applies
    dict(type="price_freeze", group="Kettle & Crumb Bakeries", list_date="2026-09-13", start="2026-09-14", end="2026-10-31", msg="M-001839"),
    # Copper Biryani Roasters street work: no delivery fee Sep 21 to Oct 16
    dict(type="fee_waiver", customer_id="C-1093", start="2026-09-21", end="2026-10-16", msg="M-001843"),
    # Bagel Kitchen competitor match from Oct 1
    dict(type="price", customer_id="C-1039", sku="NL-10154", price=40.85, start="2026-10-01", end="9999-12-31", msg="M-001846"),
    dict(type="price", customer_id="C-1039", sku="NL-10994", price=16.10, start="2026-10-01", end="9999-12-31", msg="M-001846"),
]

REFUSED = [
    dict(group="Brick Lane Cafés", what="price freeze through October", msg="M-001842"),
]
