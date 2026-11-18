"""Synthetic data with the same columns as the UCI/Kaggle 'Online Retail' dataset
(InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country)."""
import numpy as np, pandas as pd, os

def generate(path="data/online_retail.csv", n_customers=1500, seed=8):
    rng = np.random.default_rng(seed)
    products = [(f"P{1000 + i}", f"PRODUCT {i} " + rng.choice(["MUG", "LAMP", "CANDLE", "BAG", "CARD", "FRAME"]), round(rng.lognormal(1.0, .7), 2)) for i in range(300)]
    pw = rng.dirichlet(np.ones(300) * .4)
    countries = ["United Kingdom", "Germany", "France", "EIRE", "Spain", "Netherlands", "Australia", "India"]; cw = [.82, .05, .04, .03, .02, .02, .01, .01]
    rows, inv = [], 536000
    for c in range(n_customers):
        cid = 12000 + c; country = rng.choice(countries, p=cw); vip = rng.random() < .1
        first = pd.Timestamp("2010-12-01") + pd.Timedelta(days=int(rng.integers(0, 330)))
        for _ in range(1 + int(rng.gamma(1.2, 3 if not vip else 12))):
            d = first + pd.Timedelta(days=int(rng.integers(0, 365 - (first - pd.Timestamp("2010-12-01")).days + 1)))
            if d.month in (10, 11) and rng.random() < .5: d += pd.Timedelta(days=0)
            d = d.replace(hour=int(rng.choice(range(8, 19), p=np.array([2, 5, 8, 9, 10, 9, 8, 7, 5, 3, 1]) / 67)), minute=int(rng.integers(0, 60)))
            inv += 1
            for pi in rng.choice(300, int(rng.integers(1, 12)), replace=False, p=pw):
                p = products[pi]; q = int(rng.choice([1, 2, 3, 4, 6, 12, 24], p=[.3, .25, .15, .1, .1, .07, .03]))
                rows.append((str(inv), p[0], p[1], q, d.strftime("%Y-%m-%d %H:%M:%S"), p[2], float(cid), country))
            if rng.random() < .03:                                 # cancellation of the invoice
                rows.append((f"C{inv}", p[0], p[1], -q, d.strftime("%Y-%m-%d %H:%M:%S"), p[2], float(cid), country))
    df = pd.DataFrame(rows, columns=["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"])
    df.loc[rng.random(len(df)) < .22, "CustomerID"] = np.nan        # guest checkouts
    df.loc[rng.random(len(df)) < .003, "UnitPrice"] = 0
    os.makedirs(os.path.dirname(path), exist_ok=True); df.to_csv(path, index=False)
    return df

if __name__ == "__main__":
    generate(); print("Sample data written.")
