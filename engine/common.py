import pandas as pd, re, sys, os
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta

DATA = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/nl/data/merged"

def r(f):
    return pd.read_csv(os.path.join(DATA, f), dtype=str, keep_default_na=False)

def money(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def rnd(x):
    return float(Decimal(repr(float(x))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def f(x):
    try:
        return float(x)
    except Exception:
        return 0.0

HOLIDAYS = {date(2026, 9, 7), date(2026, 11, 26)}

def d(s):
    return date.fromisoformat(s[:10])

def is_bday(x):
    return x.weekday() < 5 and x not in HOLIDAYS

def add_bdays(x, n):
    while n > 0:
        x += timedelta(days=1)
        if is_bday(x):
            n -= 1
    return x

TIER = {"A": 0.10, "B": 0.06, "C": 0.03, "D": 0.0}
TAX = 0.08875

def month_of(s):
    return {"09": "september", "10": "october", "11": "november", "08": "august"}.get(s[5:7], s[5:7])
