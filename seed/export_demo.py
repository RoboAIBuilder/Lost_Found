"""Build the demo set the app ships with: app/demo_data/items.json + app/demo_data/photos/.

Run from the repo root:  python seed/export_demo.py
It reruns build.py and draw.py, then stores each item's age in days (not a fixed date),
so demo items always look recently found whenever the demo is loaded.
"""
import json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "app", "demo_data")
DAY = 86400000

subprocess.run([sys.executable, "build.py"], cwd=HERE, check=True)
subprocess.run([sys.executable, "draw.py"], cwd=HERE, check=True)
items = json.load(open(os.path.join(HERE, "items_draft.json")))
now = int(time.time() * 1000)

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(os.path.join(OUT, "photos"))
out = []
for it in items:
    n = it.get("photo_n")
    files = [f"p{n:02d}{s}.jpg" for s in (["a", "b"] if it.get("closeup") else ["a"])] if n else []
    for f in files:
        shutil.copy(os.path.join(HERE, "photos", f), os.path.join(OUT, "photos", f))
    out.append({
        "tag": it["tag"], "title": it["title"], "category": it["category"], "color": it["color"],
        "brand": it["brand"], "description": it["description"], "keywords": it["keywords"],
        "location": it["location"], "found_where": it["foundWhere"], "status": it["status"],
        "days_ago": round((now - it["foundAt"]) / DAY, 3),
        "returned_after_days": round((it["returnedAt"] - it["foundAt"]) / DAY, 3) if it.get("returnedAt") else None,
        "photos": files,
    })

claims = [
    {"email": "ava.r@example.org", "title": "Light blue Hydro Flask with soccer sticker", "name": "Ava R.", "grade": "7th, Room 214",
     "proof": "It has a soccer ball sticker and a dent on the bottom from when I dropped it at practice.", "hours_ago": 1},
    {"email": "ethan.p@example.org", "title": "Navy Nike hoodie, size M", "name": "Ethan P.", "grade": "6th, Room 108",
     "proof": "Youth medium. I left a yellow pencil in the front pocket.", "hours_ago": 2},
    {"email": "jayden.m@example.org", "title": "TI-84 Plus CE calculator", "name": "Jayden M.", "grade": "8th, Room 301",
     "proof": "My initials J.M. are on the back in white marker.", "hours_ago": 3},
    {"email": "liam.k@example.org", "title": "Navy Nike hoodie, size M", "name": "Liam K.", "grade": "6th, Room 110",
     "proof": "It's navy and says Nike on it.", "hours_ago": 4},
]
json.dump({"items": out, "claims": claims}, open(os.path.join(OUT, "items.json"), "w"), indent=1)
print(f"{len(out)} items, {sum(len(i['photos']) for i in out)} photos, {len(claims)} claims -> {OUT}")
