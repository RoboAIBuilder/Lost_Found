"""Demo data: 121 middle-school items (35 with photos) and 4 pending claims, all marked mock=1.

Used by the "Reset demo data" button (test mode) and by seed_mock.py. Works with SQLite or Postgres,
and with the local photo folder or Vercel Blob, through the store/remove functions app.py passes in.
"""
import json, os, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "demo_data")
DAY = 86400000

def clear(conn, remove_photo):
    """Remove only demo rows and their photos. Items and claims staff created stay."""
    for r in conn.execute("SELECT photos FROM items WHERE mock=1").fetchall():
        for p in json.loads(r["photos"] or "[]"):
            remove_photo(p)
    conn.execute("DELETE FROM claims WHERE mock=1")
    conn.execute("DELETE FROM items WHERE mock=1")
    conn.commit()

def load(conn, store_photo, remove_photo):
    clear(conn, remove_photo)
    data = json.load(open(os.path.join(DATA, "items.json")))
    now = int(time.time() * 1000)
    used_tags = {r["tag"] for r in conn.execute("SELECT tag FROM items").fetchall()}
    rows, ids_by_title = [], {}
    for it in data["items"]:
        if it["tag"] in used_tags:
            continue
        names = []
        for f in it["photos"]:
            name = uuid.uuid4().hex + ".jpg"
            with open(os.path.join(DATA, "photos", f), "rb") as fh:
                store_photo(name, fh.read())
            names.append(name)
        found_at = now - int(it["days_ago"] * DAY)
        returned_at = found_at + int(it["returned_after_days"] * DAY) if it.get("returned_after_days") else None
        item_id = uuid.uuid4().hex[:12]
        ids_by_title[it["title"]] = item_id
        rows.append((item_id, it["tag"], it["title"], it["category"], it["color"], it["brand"], it["description"],
                     json.dumps(it["keywords"]), json.dumps(names), it["location"], it["found_where"], found_at,
                     it["status"], returned_at))
    conn.executemany("""INSERT INTO items (id, tag, title, category, color, brand, description, keywords, photos,
                        location, found_where, found_at, status, returned_at, mock)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""", rows)
    claims = [(ids_by_title[c["title"]], c["email"], c["name"], c["grade"], c["proof"], now - c["hours_ago"] * 3600000)
              for c in data["claims"] if c["title"] in ids_by_title]
    conn.executemany("""INSERT INTO claims (item_id, student_email, name, grade, proof, created_at, mock)
                        VALUES (?,?,?,?,?,?,1)""", claims)
    conn.commit()
    return len(rows), len(claims)
