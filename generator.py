import csv, random, time
from datetime import datetime, timedelta

FILE = "sales.csv"
PRODUCTS = {"Headphones": 80, "Keyboard": 50, "Mouse": 25, "Monitor": 200}  # name: price
REGIONS = ["North", "South", "East", "West"]

def make_sale(ts, spike=False):
    if spike and random.random() < 0.7:
        product, region = "Headphones", "North"   # the hidden surprise
    else:
        product, region = random.choice(list(PRODUCTS)), random.choice(REGIONS)
    amount = round(PRODUCTS[product] * random.uniform(0.9, 1.1), 2)
    return [ts.strftime("%Y-%m-%d %H:%M:%S"), product, region, amount]

# 1. Create 2 hours of past sales, so the agent knows what "normal" looks like
with open(FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["ts", "product", "region", "amount"])
    now = datetime.now()
    t = now - timedelta(hours=2)
    while t < now:
        writer.writerow(make_sale(t))
        t += timedelta(seconds=random.uniform(1, 4))

# 2. Keep adding new sales forever, like a real shop
print("Wrote 2 hours of history. Now adding live sales... (Ctrl+C to stop)")
start = time.time()
while True:
    seconds_running = time.time() - start
    spike = 180 < seconds_running < 300   # a sales surge between minutes 3 and 5
    try:
        with open(FILE, "a", newline="") as f:
            csv.writer(f).writerow(make_sale(datetime.now(), spike))
    except PermissionError:
        time.sleep(0.5)   # file is busy (being read or scanned), so try again shortly
        continue
    time.sleep(0.3 if spike else random.uniform(1, 4))