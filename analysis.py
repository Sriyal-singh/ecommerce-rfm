# %%
# # E-commerce Customer Behaviour & RFM Analysis
# Dataset: "Online Retail" (UCI / Kaggle) -> `data/online_retail.csv` (synthetic sample used if missing).

# %%
import os
import pandas as pd, numpy as np
import matplotlib.pyplot as plt, seaborn as sns
sns.set_theme(style="whitegrid")
os.makedirs("images", exist_ok=True)
PATH = "data/online_retail.csv"
if not os.path.exists(PATH):
    from generate_data import generate
    generate(PATH)
try:
    raw = pd.read_csv(PATH)
except UnicodeDecodeError:
    raw = pd.read_csv(PATH, encoding="latin-1")
raw.head()

# %%
# ## 1. Cleaning
# - Cancellations (invoice starts with "C") are separated, not silently dropped
# - Remove rows with no CustomerID for customer-level work (guest checkouts), non-positive quantity/price, duplicates
raw["InvoiceNo"] = raw["InvoiceNo"].astype(str)
cancels = raw[raw["InvoiceNo"].str.startswith("C")]
df = raw[~raw["InvoiceNo"].str.startswith("C")].dropna(subset=["CustomerID"]).drop_duplicates()
df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)].copy()
df["CustomerID"] = df["CustomerID"].astype(int)
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["Revenue"] = df["Quantity"] * df["UnitPrice"]
df["Month"] = df["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
print(f"Raw rows {len(raw):,} -> clean {len(df):,} | cancellations {len(cancels):,} | customers {df['CustomerID'].nunique():,}")
df.to_csv("cleaned_dataset.csv", index=False)

# %%
# ## 2. Repeat customers & average basket size
orders_per_cust = df.groupby("CustomerID")["InvoiceNo"].nunique()
repeat_pct = (orders_per_cust > 1).mean() * 100
basket = df.groupby("InvoiceNo").agg(items=("Quantity", "sum"), lines=("StockCode", "nunique"), value=("Revenue", "sum"))
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
ax[0].pie([repeat_pct, 100 - repeat_pct], labels=["Repeat", "One-time"], autopct="%1.1f%%", colors=["#2a9d8f", "#e9c46a"], startangle=90); ax[0].set_title("Repeat vs one-time customers")
sns.histplot(orders_per_cust.clip(upper=20), bins=20, ax=ax[1], color="#264653"); ax[1].set_title("Orders per customer (capped at 20)")
sns.histplot(basket["value"].clip(upper=basket["value"].quantile(.98)), bins=40, ax=ax[2], color="#e76f51"); ax[2].set_title(f"Basket value (mean {basket['value'].mean():.0f})")
plt.tight_layout(); plt.savefig("images/repeat_and_basket.png", dpi=150); plt.show()

# %%
# ## 3. Revenue by country & top products
by_country = df.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
top_prod = df.groupby("Description")["Revenue"].sum().sort_values(ascending=False).head(10)
fig, ax = plt.subplots(1, 2, figsize=(14, 5))
by_country.head(8).iloc[::-1].plot.barh(ax=ax[0], color="#264653").set_title("Revenue by country (top 8)")
top_prod.iloc[::-1].plot.barh(ax=ax[1], color="#2a9d8f").set_title("Top 10 products by revenue")
plt.tight_layout(); plt.savefig("images/country_products.png", dpi=150); plt.show()

# %%
# ## 4. Seasonal trends
monthly = df.groupby("Month")["Revenue"].sum()
df["Weekday"] = df["InvoiceDate"].dt.day_name(); df["Hour"] = df["InvoiceDate"].dt.hour
heat = df.pivot_table(index="Weekday", columns="Hour", values="Revenue", aggfunc="sum").reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
fig, ax = plt.subplots(1, 2, figsize=(15, 4.5))
monthly.plot(ax=ax[0], marker="o", color="#e76f51"); ax[0].set_title("Monthly revenue")
sns.heatmap(heat, cmap="YlOrRd", ax=ax[1], cbar_kws={"label": "Revenue"}); ax[1].set_title("When do customers buy? (weekday x hour)")
plt.tight_layout(); plt.savefig("images/seasonality.png", dpi=150); plt.show()

# %%
# ## 5. RFM analysis
# Recency = days since last purchase, Frequency = number of invoices, Monetary = total spend. Each is scored 1-5 (5 = best).
snapshot = df["InvoiceDate"].max() + pd.Timedelta(days=1)
rfm = df.groupby("CustomerID").agg(Recency=("InvoiceDate", lambda s: (snapshot - s.max()).days), Frequency=("InvoiceNo", "nunique"), Monetary=("Revenue", "sum"))
rfm["R"] = pd.qcut(rfm["Recency"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M"] = pd.qcut(rfm["Monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
def segment(r):
    if r.R >= 4 and r.F >= 4: return "Champions"
    if r.R >= 3 and r.F >= 3: return "Loyal"
    if r.R >= 4 and r.F <= 2: return "New / Promising"
    if r.R <= 2 and r.F >= 4: return "Can't lose them"
    if r.R <= 2 and r.F >= 2: return "At risk"
    return "Hibernating"
rfm["Segment"] = rfm.apply(segment, axis=1)
seg = rfm.groupby("Segment").agg(customers=("R", "size"), avg_recency=("Recency", "mean"), avg_frequency=("Frequency", "mean"), revenue=("Monetary", "sum")).sort_values("revenue", ascending=False)
rfm.to_csv("rfm_segments.csv")
fig, ax = plt.subplots(1, 2, figsize=(14, 5))
seg["customers"].plot.bar(ax=ax[0], color="#264653", rot=30).set_title("Customers per RFM segment")
seg["revenue"].plot.pie(ax=ax[1], autopct="%1.0f%%", ylabel="").set_title("Revenue share by segment")
plt.tight_layout(); plt.savefig("images/rfm_segments.png", dpi=150); plt.show()
seg.round(1)

# %%
# ## 6. Insights
print("Insights:")
print(f"1. {repeat_pct:.0f}% of customers are repeat buyers")
print(f"2. Average basket: {basket['lines'].mean():.1f} product lines, {basket['items'].mean():.0f} units, value {basket['value'].mean():.0f}")
print(f"3. {by_country.index[0]} generates {by_country.iloc[0] / by_country.sum():.0%} of revenue")
print(f"4. Peak month: {monthly.idxmax():%B %Y}")
print(f"5. '{seg.index[0]}' customers are {seg.iloc[0]['customers'] / seg['customers'].sum():.0%} of the base but {seg.iloc[0]['revenue'] / seg['revenue'].sum():.0%} of revenue")
