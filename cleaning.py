"""
Reusable cleaning + data-quality audit functions for the Duka Electronics capstone.

Main entry points
-----------------
audit_quality(orders, customers, products)  -> DataFrame (six-dimension audit)
clean_data(orders, customers, products)     -> (dict of clean tables, cleaning-log DataFrame)

Every cleaning step is recorded in the log (table, step, issue, rows affected,
action, justification) so the pipeline is transparent and repeatable.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np
import pandas as pd

WINDOW_START = pd.Timestamp("2026-01-01")
WINDOW_END = pd.Timestamp("2026-06-30")
STD_BRANCHES = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"]
BRANCH_ALIASES = {"nbi": "Nairobi", "msa": "Mombasa", "eld": "Eldoret"}
CATEGORY_MAP = {"laptops": "Laptops", "smartphones": "Smartphones", "tvs": "TVs", "audio": "Audio",
                "accessories": "Accessories", "appliances": "Appliances"}
PAYMENT_MAP = {"mpesa": "M-Pesa", "m-pesa": "M-Pesa", "cash": "Cash", "card": "Card",
               "bank transfer": "Bank Transfer"}
MAX_PLAUSIBLE_QTY = 10          # the largest legitimate basket line is 4 units
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ------------------------------------------------------------------ helpers
def _log(entries: list, table: str, step: str, issue: str, rows: int, action: str, why: str):
    entries.append({"table": table, "step": step, "issue": issue,
                    "rows_affected": int(rows), "action": action, "justification": why})


def _std_branch(s: pd.Series) -> pd.Series:
    key = s.astype("string").str.strip().str.lower()
    key = key.replace(BRANCH_ALIASES)
    return key.str.title()


def _parse_dates(s: pd.Series) -> pd.Series:
    """ISO first, then day-first (dd/mm/yyyy). Unparseable -> NaT."""
    s = s.astype("string").str.strip()
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    dmy = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    return iso.fillna(dmy)


def _pseudonymise(ids: pd.Series, salt: str) -> pd.Series:
    def h(x):
        if pd.isna(x):
            return "UNKNOWN"
        return "K" + hashlib.sha256((salt + str(x)).encode()).hexdigest()[:10]
    return ids.map(h)


# -------------------------------------------------------------------- audit
def audit_quality(orders: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Six-dimension audit on RAW data. Returns one row per check."""
    rows = []

    def add(dim, table, check, n, total):
        rows.append({"dimension": dim, "table": table, "check": check,
                     "issues": int(n), "total_rows": int(total),
                     "pct": round(100 * n / total, 2) if total else 0.0})

    o, c, p = orders, customers, products
    N, NC = len(o), len(c)

    # 1 Completeness
    for col in ["customer_id", "payment_method", "unit_price", "channel"]:
        add("Completeness", "orders", f"missing {col}", o[col].isna().sum(), N)
    add("Completeness", "customers", "missing age", c["age"].isna().sum(), NC)
    add("Completeness", "customers", "missing email", c["email"].isna().sum(), NC)
    add("Completeness", "customers", "missing county", c["county"].isna().sum(), NC)
    add("Completeness", "products", "missing list_price_kes", p["list_price_kes"].isna().sum(), len(p))

    # 2 Validity
    qty = pd.to_numeric(o["quantity"], errors="coerce")
    add("Validity", "orders", f"quantity <= 0 or > {MAX_PLAUSIBLE_QTY}", ((qty <= 0) | (qty > MAX_PLAUSIBLE_QTY)).sum(), N)
    d = _parse_dates(o["order_date"])
    add("Validity", "orders", "unparseable order_date", d.isna().sum(), N)
    add("Validity", "customers", "age outside 18-90", ((c["age"] < 18) | (c["age"] > 90)).sum(), NC)
    bad_email = c["email"].notna() & ~c["email"].astype("string").str.match(EMAIL_RE)
    add("Validity", "customers", "malformed email", bad_email.sum(), NC)
    add("Validity", "orders", "product_id not in products (orphan)", (~o["product_id"].isin(p["product_id"])).sum(), N)
    add("Validity", "orders", "customer_id not in customers (orphan)",
        (o["customer_id"].notna() & ~o["customer_id"].isin(c["customer_id"])).sum(), N)

    # 3 Accuracy
    price = pd.to_numeric(o["unit_price"], errors="coerce")
    lp = o["product_id"].map(p.set_index("product_id")["list_price_kes"])
    ratio = price / lp
    add("Accuracy", "orders", "unit_price > 3x product list price", (ratio > 3).sum(), N)
    add("Accuracy", "orders", "unit_price < 0.3x product list price", (ratio < 0.3).sum(), N)

    # 4 Consistency
    add("Consistency", "orders", "branch labels not in standard list", (~o["branch"].isin(STD_BRANCHES)).sum(), N)
    add("Consistency", "orders", "dates not in ISO yyyy-mm-dd",
        (~o["order_date"].astype("string").str.match(r"^\d{4}-\d{2}-\d{2}$")).sum(), N)
    add("Consistency", "orders", "discount_pct stored as text with '%'",
        o["discount_pct"].astype("string").str.contains("%", na=False).sum(), N)
    add("Consistency", "orders", "payment_method label variants",
        (~o["payment_method"].isna() & ~o["payment_method"].isin(["M-Pesa", "Cash", "Card", "Bank Transfer"])).sum(), N)
    add("Consistency", "products", "category casing variants",
        (~p["category"].isin(CATEGORY_MAP.values())).sum(), len(p))
    add("Consistency", "customers", "phone not in 07xxxxxxxx form", (~c["phone"].astype("string").str.match(r"^07\d{8}$")).sum(), NC)

    # 5 Uniqueness
    add("Uniqueness", "orders", "exact duplicate rows", o.duplicated().sum(), N)
    add("Uniqueness", "orders", "duplicate order_id", o["order_id"].duplicated().sum(), N)
    add("Uniqueness", "customers", "duplicate customer_id", c["customer_id"].duplicated().sum(), NC)

    # 6 Timeliness
    add("Timeliness", "orders", "dated after reporting window end (30-Jun-2026)", (d > WINDOW_END).sum(), N)
    add("Timeliness", "orders", "dated before window start (1-Jan-2026)", (d < WINDOW_START).sum(), N)
    return pd.DataFrame(rows)


# -------------------------------------------------------------------- clean
def clean_data(orders: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame,
               salt: str = "duka-capstone-2026"):
    """
    Clean the three raw tables.

    Returns
    -------
    tables : dict[str, DataFrame]   keys: orders, customers, products
    log    : DataFrame              one row per cleaning step
    """
    L: list = []
    o, c, p = orders.copy(), customers.copy(), products.copy()

    # ---------------- PRODUCTS
    for col in ["product_id", "product_name", "category"]:
        p[col] = p[col].astype("string").str.strip()
    n = (~p["category"].isin(CATEGORY_MAP.values())).sum()
    p["category"] = p["category"].str.lower().map(CATEGORY_MAP)
    _log(L, "products", "standardise", "category casing variants", n, "Mapped to canonical category names",
         "Same category must map to one label or group-bys split it.")

    # ---------------- CUSTOMERS
    for col in ["customer_id", "county", "email"]:
        c[col] = c[col].astype("string").str.strip()
    n = c.duplicated().sum()
    c = c.drop_duplicates()
    n2 = c["customer_id"].duplicated().sum()
    c = c.drop_duplicates(subset="customer_id", keep="first")
    _log(L, "customers", "deduplicate", "duplicate customer rows", n + n2, "Dropped duplicates, kept first",
         "customer_id is the primary key; duplicates inflate customer counts.")
    bad_age = ((c["age"] < 18) | (c["age"] > 90)).sum()
    c.loc[(c["age"] < 18) | (c["age"] > 90), "age"] = np.nan
    _log(L, "customers", "validity", "impossible ages (0, 150, 999)", bad_age, "Set to missing",
         "Customers must be adults; values are entry errors, not recoverable.")
    n_missing_age = c["age"].isna().sum()
    c["age_band"] = pd.cut(c["age"], [17, 24, 34, 44, 54, 90],
                           labels=["18-24", "25-34", "35-44", "45-54", "55+"]).astype("string").fillna("Unknown")
    _log(L, "customers", "privacy", "exact age is quasi-identifying", len(c),
         "Replaced age with age_band", "Banding reduces re-identification risk (Ethics statement).")
    n = c["county"].isna().sum()
    c["county"] = c["county"].fillna("Unknown")
    _log(L, "customers", "completeness", "missing county", n, "Filled with 'Unknown'",
         "Keeps the row for analysis; avoids guessing a location.")
    c["customer_key"] = _pseudonymise(c["customer_id"], salt)
    _log(L, "customers", "privacy", "direct identifiers (name, phone, email)", len(c),
         "Dropped full_name, phone, email; customer_id replaced by salted SHA-256 key",
         "Analysis needs no direct identifiers; protects individuals under Kenya Data Protection Act 2019.")
    valid_ids = set(c["customer_id"])
    c["signup_date"] = pd.to_datetime(c["signup_date"], errors="coerce")
    c_clean = c[["customer_key", "county", "age_band", "signup_date"]].reset_index(drop=True)

    # ---------------- ORDERS
    n = o.duplicated().sum()
    o = o.drop_duplicates()
    n2 = o["order_id"].duplicated().sum()
    o = o.drop_duplicates(subset="order_id", keep="first")
    _log(L, "orders", "deduplicate", "exact duplicate order lines", n + n2, "Dropped duplicates",
         "Duplicates double-count revenue.")

    before = o["branch"].astype("string").str.strip()
    o["branch"] = _std_branch(o["branch"])
    n = (before != o["branch"]).sum()
    _log(L, "orders", "standardise", "branch spelling / case / abbreviations", n,
         "Trimmed, title-cased, mapped Nbi/Msa/Eld to full names",
         "Otherwise one branch appears as several.")

    parsed = _parse_dates(o["order_date"])
    n_noniso = (~o["order_date"].astype("string").str.match(r"^\d{4}-\d{2}-\d{2}$")).sum()
    o["order_date"] = parsed
    _log(L, "orders", "standardise", "mixed date formats (dd/mm/yyyy)", n_noniso,
         "Parsed to datetime (ISO first, then day-first)", "Kenyan convention is day-first.")
    bad = o["order_date"].isna() | (o["order_date"] > WINDOW_END) | (o["order_date"] < WINDOW_START)
    _log(L, "orders", "timeliness", "dates outside Jan-Jun 2026 window", bad.sum(), "Dropped rows",
         "Future dates are impossible; true date unknown, so cannot be corrected.")
    o = o[~bad]

    n_pct = o["discount_pct"].astype("string").str.contains("%", na=False).sum()
    o["discount_pct"] = pd.to_numeric(o["discount_pct"].astype("string").str.replace("%", "", regex=False).str.strip(),
                                      errors="coerce").fillna(0)
    _log(L, "orders", "standardise", "discount_pct stored as text ('10%')", n_pct,
         "Stripped '%' and converted to numeric", "Needed for arithmetic and averaging.")

    pm = o["payment_method"].astype("string").str.strip().str.lower().map(PAYMENT_MAP)
    n = (o["payment_method"].notna() & ~o["payment_method"].isin(["M-Pesa", "Cash", "Card", "Bank Transfer"])).sum()
    o["payment_method"] = pm.fillna("Unknown")
    _log(L, "orders", "standardise", "payment label variants (mpesa, M-PESA, cash ...)", n,
         "Mapped to 4 standard labels", "Consistent categories.")
    n = o["payment_method"].eq("Unknown").sum()
    _log(L, "orders", "completeness", "missing payment_method", n, "Labelled 'Unknown'",
         "Cannot infer payment type; kept so revenue is not lost.")
    n = o["channel"].isna().sum()
    o["channel"] = o["channel"].astype("string").str.strip().fillna("Unknown")
    _log(L, "orders", "completeness", "missing channel", n, "Labelled 'Unknown'", "Same reasoning as payment_method.")

    o["quantity"] = pd.to_numeric(o["quantity"], errors="coerce")
    bad = o["quantity"].isna() | (o["quantity"] <= 0) | (o["quantity"] > MAX_PLAUSIBLE_QTY)
    _log(L, "orders", "validity", f"quantity <=0 or >{MAX_PLAUSIBLE_QTY} (returns keyed as -1, bulk typos)", bad.sum(),
         "Dropped rows", "Not a valid sale line; returns are tracked via order_status, not negative qty.")
    o = o[~bad]

    orphan_p = ~o["product_id"].isin(p["product_id"])
    _log(L, "orders", "integrity", "product_id not in products", orphan_p.sum(), "Dropped rows",
         "Cannot assign category or validate price.")
    o = o[~orphan_p]

    # price: impute / repair using the product's list price
    lp = o["product_id"].map(p.set_index("product_id")["list_price_kes"])
    o["unit_price"] = pd.to_numeric(o["unit_price"], errors="coerce")
    # products with a missing list price: use median observed order price
    med = o.groupby("product_id")["unit_price"].median()
    lp = lp.fillna(o["product_id"].map(med))
    p["list_price_kes"] = p["list_price_kes"].fillna(p["product_id"].map(med))
    ratio = o["unit_price"] / lp
    slip = ratio.between(8, 12)
    o.loc[slip, "unit_price"] = (o.loc[slip, "unit_price"] / 10).round(0)
    _log(L, "orders", "accuracy", "unit_price ~10x list price (decimal slip)", slip.sum(),
         "Divided by 10", "Ratio of 8-12x is a systematic keying error with a clear fix.")
    ratio = o["unit_price"] / lp
    bad = (ratio > 3) | (ratio < 0.3)
    _log(L, "orders", "accuracy", "other extreme unit_price vs list price", bad.sum(), "Dropped rows",
         "No defensible correction.")
    o = o[~bad]
    n = o["unit_price"].isna().sum()
    o["unit_price"] = o["unit_price"].fillna(lp[o.index])
    _log(L, "orders", "completeness", "missing unit_price", n, "Imputed with product list price",
         "Branch prices vary only ~1.5%, so list price is a safe proxy.")

    n_miss = o["customer_id"].isna().sum()
    n_orph = (o["customer_id"].notna() & ~o["customer_id"].isin(valid_ids)).sum()
    o["customer_key"] = _pseudonymise(o["customer_id"].where(o["customer_id"].isin(valid_ids)), salt)
    _log(L, "orders", "integrity", "missing or unmatched customer_id", n_miss + n_orph,
         "Set customer_key = 'UNKNOWN'; kept row", "The sale is real even if the buyer is unknown.")

    # derived measures
    o["gross_revenue"] = o["quantity"] * o["unit_price"]
    o["discount_kes"] = o["gross_revenue"] * o["discount_pct"] / 100
    o["net_revenue"] = o["gross_revenue"] - o["discount_kes"]
    o["month"] = o["order_date"].dt.to_period("M").astype(str)
    o["quarter"] = "Q" + o["order_date"].dt.quarter.astype(str)
    o["is_completed"] = (o["order_status"] == "Completed").astype(int)
    _log(L, "orders", "derive", "derived columns", len(o),
         "Added gross_revenue, discount_kes, net_revenue, month, quarter, is_completed",
         "Single, documented definition of revenue used by SQL and Python.")

    o_clean = o[["order_id", "order_date", "month", "quarter", "branch", "product_id", "quantity", "unit_price",
                 "discount_pct", "gross_revenue", "discount_kes", "net_revenue", "customer_key", "channel",
                 "payment_method", "order_status", "is_completed"]].reset_index(drop=True)
    o_clean["order_date"] = o_clean["order_date"].dt.strftime("%Y-%m-%d")
    p_clean = p[["product_id", "product_name", "category", "list_price_kes"]].reset_index(drop=True)
    c_clean["signup_date"] = c_clean["signup_date"].dt.strftime("%Y-%m-%d")

    _log(L, "orders", "result", "rows raw -> clean", len(orders) - len(o_clean), "see counts",
         f"{len(orders):,} raw -> {len(o_clean):,} clean order lines")
    log = pd.DataFrame(L)
    return {"orders": o_clean, "customers": c_clean, "products": p_clean}, log
