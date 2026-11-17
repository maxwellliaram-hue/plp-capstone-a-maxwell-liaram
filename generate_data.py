"""
Synthetic data generator for the Duka Electronics capstone (H1 2026).

Produces three deliberately messy "raw" CSV files in data/raw/:
    customers_raw.csv, products_raw.csv, orders_raw.csv

The data is SIMULATED (no real people). Run:  python data/generate_data.py
A fixed seed makes the output fully reproducible.
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 2026
rng = np.random.default_rng(SEED)
OUT = Path(__file__).parent / "raw"
OUT.mkdir(exist_ok=True)

# ----------------------------------------------------------------- products
products = [
    ("P001", "ProBook 14 Laptop", "Laptops", 78000),
    ("P002", "ProBook 15 Laptop", "Laptops", 92000),
    ("P003", "UltraSlim 13 Laptop", "Laptops", 125000),
    ("P004", "StudyMate Laptop", "Laptops", 48000),
    ("P005", "Galaxy-style A15 Phone", "Smartphones", 24000),
    ("P006", "Galaxy-style S24 Phone", "Smartphones", 89000),
    ("P007", "Tecno-style Spark Phone", "Smartphones", 14500),
    ("P008", "iPhone-style 15 Phone", "Smartphones", 135000),
    ("P009", "Smart TV 43in", "TVs", 38000),
    ("P010", "Smart TV 55in", "TVs", 62000),
    ("P011", "Smart TV 32in", "TVs", 21000),
    ("P012", "Soundbar 2.1", "Audio", 15500),
    ("P013", "Bluetooth Speaker", "Audio", 6500),
    ("P014", "Wireless Earbuds", "Audio", 4800),
    ("P015", "Headphones Over-Ear", "Audio", 9500),
    ("P016", "Phone Charger 20W", "Accessories", 1500),
    ("P017", "USB-C Cable", "Accessories", 800),
    ("P018", "Laptop Bag", "Accessories", 3200),
    ("P019", "Power Bank 20000mAh", "Accessories", 3800),
    ("P020", "Wireless Mouse", "Accessories", 1800),
    ("P021", "Microwave 25L", "Appliances", 14500),
    ("P022", "Blender 1.5L", "Appliances", 5200),
    ("P023", "Electric Kettle", "Appliances", 2800),
    ("P024", "Air Fryer 5L", "Appliances", 11500),
]
prod_df = pd.DataFrame(products, columns=["product_id", "product_name", "category", "list_price_kes"])

cat_weight = {"Laptops": 0.07, "Smartphones": 0.16, "TVs": 0.07, "Audio": 0.17,
              "Accessories": 0.38, "Appliances": 0.15}
w = prod_df["category"].map(cat_weight).to_numpy()
w = w / w.sum()

# ---------------------------------------------------------------- customers
N_CUST = 3000
first = ["Wanjiru", "Otieno", "Achieng", "Kamau", "Mwangi", "Njeri", "Odhiambo", "Atieno",
         "Kiptoo", "Chebet", "Hassan", "Fatuma", "Mutua", "Nduta", "Wafula", "Naliaka",
         "Omondi", "Akinyi", "Kariuki", "Wambui", "Barasa", "Juma", "Zawadi", "Kimani"]
last = ["Mwangi", "Ochieng", "Kibet", "Maina", "Njoroge", "Otieno", "Mohamed", "Wekesa",
        "Karanja", "Rotich", "Abdalla", "Mutiso", "Nyambura", "Onyango", "Kiplagat", "Waweru"]
counties = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Uasin Gishu", "Kiambu", "Machakos", "Kakamega"]
cust = pd.DataFrame({
    "customer_id": [f"C{i:05d}" for i in range(1, N_CUST + 1)],
    "full_name": [f"{rng.choice(first)} {rng.choice(last)}" for _ in range(N_CUST)],
    "phone": ["07" + "".join(map(str, rng.integers(0, 10, 8))) for _ in range(N_CUST)],
    "age": rng.normal(34, 11, N_CUST).round().clip(18, 75),
    "county": rng.choice(counties, N_CUST, p=[.34, .17, .11, .13, .11, .06, .04, .04]),
})
cust["email"] = (cust["full_name"].str.lower().str.replace(" ", ".") +
                 cust["customer_id"].str[-3:] + "@example.com")
cust["signup_date"] = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 900, N_CUST), unit="D")

# --- inject quality issues (customers)
cust.loc[rng.choice(N_CUST, 150, replace=False), "age"] = np.nan
cust.loc[rng.choice(N_CUST, 12, replace=False), "age"] = rng.choice([0, 150, 999], 12)
cust.loc[rng.choice(N_CUST, 90, replace=False), "email"] = np.nan
cust.loc[rng.choice(N_CUST, 25, replace=False), "email"] = "not_an_email"
ph_idx = rng.choice(N_CUST, 300, replace=False)
cust.loc[ph_idx, "phone"] = cust.loc[ph_idx, "phone"].str.replace(r"^0", "+254", regex=True)
cust.loc[rng.choice(N_CUST, 60, replace=False), "county"] = None
cust = pd.concat([cust, cust.sample(40, random_state=SEED)], ignore_index=True)   # duplicates
cust["signup_date"] = cust["signup_date"].dt.strftime("%Y-%m-%d")

# ------------------------------------------------------------------- orders
branches = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"]
base_share = np.array([0.36, 0.20, 0.13, 0.17, 0.14])
mult = {  # monthly demand multiplier (Jan..Jun) - builds the story
    "Nairobi": [1.00, 1.00, 1.04, 1.02, 1.06, 1.08],
    "Mombasa": [1.05, 1.06, 1.04, 0.86, 0.80, 0.76],
    "Kisumu":  [1.00, 0.98, 1.02, 1.03, 1.05, 1.04],
    "Nakuru":  [1.04, 1.05, 1.03, 0.88, 0.82, 0.78],
    "Eldoret": [0.70, 0.74, 0.80, 1.05, 1.18, 1.30],
}
days = pd.date_range("2026-01-01", "2026-06-30")
rows = []
BASE_DAILY = 80
for d in days:
    m = d.month - 1
    dow = 1.25 if d.dayofweek >= 4 else 1.0
    for b, sh in zip(branches, base_share):
        n_lines = rng.poisson(BASE_DAILY * sh * mult[b][m] * dow)
        rows.extend([(d, b)] * n_lines)
orders = pd.DataFrame(rows, columns=["order_date", "branch"])
n = len(orders)
pidx = rng.choice(len(prod_df), n, p=w)
orders["product_id"] = prod_df["product_id"].to_numpy()[pidx]
list_price = prod_df["list_price_kes"].to_numpy()[pidx]
cat = prod_df["category"].to_numpy()[pidx]
orders["quantity"] = np.where(cat == "Accessories", rng.choice([1, 2, 3, 4], n, p=[.55, .25, .12, .08]),
                      np.where(np.isin(cat, ["Laptops", "TVs"]), rng.choice([1, 2], n, p=[.93, .07]),
                               rng.choice([1, 2, 3], n, p=[.8, .15, .05])))
orders["unit_price"] = (list_price * rng.normal(1.0, 0.015, n)).round(0)
orders["discount_pct"] = rng.choice([0, 5, 10, 15], n, p=[.6, .2, .15, .05])
orders["customer_id"] = [f"C{i:05d}" for i in rng.integers(1, N_CUST + 1, n)]
orders["channel"] = rng.choice(["In-store", "Online"], n, p=[.72, .28])
orders["payment_method"] = np.where(
    orders["channel"] == "Online",
    rng.choice(["M-Pesa", "Card", "Bank Transfer"], n, p=[.62, .30, .08]),
    rng.choice(["M-Pesa", "Cash", "Card", "Bank Transfer"], n, p=[.46, .38, .13, .03]))
orders["order_status"] = rng.choice(["Completed", "Returned", "Cancelled"], n, p=[.92, .05, .03])
orders = orders.sample(frac=1, random_state=SEED).reset_index(drop=True)
orders.insert(0, "order_id", [f"O{i:06d}" for i in range(1, n + 1)])


def idx(frac):
    return rng.choice(n, int(n * frac), replace=False)

# --- inject quality issues (orders)
variants = {"Nairobi": ["nairobi", "NAIROBI", "Nbi", "Nairobi "], "Mombasa": ["mombasa", "MOMBASA", "Msa"],
            "Kisumu": ["kisumu", "KISUMU "], "Nakuru": ["nakuru", "NAKURU"], "Eldoret": ["eldoret", "ELDORET", "Eld "]}
for i in idx(0.05):
    orders.loc[i, "branch"] = rng.choice(variants[orders.loc[i, "branch"]])
orders["order_date"] = orders["order_date"].dt.strftime("%Y-%m-%d")
for i in idx(0.03):                                   # mixed date format
    orders.loc[i, "order_date"] = pd.to_datetime(orders.loc[i, "order_date"]).strftime("%d/%m/%Y")
orders.loc[idx(0.002), "order_date"] = "2027-03-15"   # impossible future date
orders.loc[idx(0.03), "payment_method"] = np.nan
orders.loc[idx(0.015), "customer_id"] = np.nan
orders.loc[idx(0.01), "unit_price"] = np.nan
orders.loc[idx(0.006), "channel"] = np.nan
orders["discount_pct"] = orders["discount_pct"].astype(object)
for i in idx(0.02):                                   # "10%" strings
    orders.loc[i, "discount_pct"] = f"{orders.loc[i, 'discount_pct']}%"
orders.loc[idx(0.003), "quantity"] = -1
orders.loc[idx(0.002), "quantity"] = rng.choice([100, 500, 999], int(n * 0.002))
for i in idx(0.003):                                  # decimal-slip price outliers
    if pd.notna(orders.loc[i, "unit_price"]):
        orders.loc[i, "unit_price"] *= 10
orders.loc[idx(0.002), "product_id"] = "P999"         # orphan product
orders.loc[idx(0.003), "customer_id"] = "C99999"      # orphan customer
for i in idx(0.04):                                   # payment label variants
    orders.loc[i, "payment_method"] = rng.choice(["mpesa", "M-PESA", "Mpesa", "cash", "CARD"])
orders = pd.concat([orders, orders.sample(int(n * 0.02), random_state=SEED)], ignore_index=True)  # duplicates
orders = orders.sample(frac=1, random_state=1).reset_index(drop=True)

prod_raw = prod_df.copy()
prod_raw.loc[3, "category"] = "laptops"
prod_raw.loc[13, "category"] = "AUDIO"
prod_raw.loc[16, "list_price_kes"] = np.nan

cust.to_csv(OUT / "customers_raw.csv", index=False)
prod_raw.to_csv(OUT / "products_raw.csv", index=False)
orders.to_csv(OUT / "orders_raw.csv", index=False)
print(f"customers_raw: {len(cust):,} | products_raw: {len(prod_raw)} | orders_raw: {len(orders):,}")
