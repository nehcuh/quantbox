from pymongo import MongoClient
import pandas as pd

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27018")
db = client.quantbox

# Query trade dates
cursor = db.trade_date.find(
    {
        "exchange": "SHSE",
        "trade_date": {"$gte": "2024-01-01", "$lte": "2024-01-10"}
    },
    {"_id": 0}
).sort("trade_date", 1)

# Convert to DataFrame
df = pd.DataFrame(list(cursor))
print("\nTrade dates in database:")
print(df["trade_date"])
