"""Load 121 mock middle-school items (35 with photos) and 4 pending claims for demos.

  python seed_mock.py          add the mock data (replaces any earlier mock data)
  python seed_mock.py --clear  remove only the mock data; items staff logged stay
"""
import json, os, shutil, sqlite3, subprocess, sys, time, uuid

import app as lf  # creates the database if needed

SEED = os.path.join(os.path.dirname(lf.HERE), "seed")

def clear(c):
    for (photos,) in c.execute("SELECT photos FROM items WHERE mock=1"):
        for p in json.loads(photos or "[]"):
            try: os.remove(os.path.join(lf.PHOTO_DIR, p))
            except OSError: pass
    c.execute("DELETE FROM claims WHERE mock=1")
    c.execute("DELETE FROM items WHERE mock=1")

def main():
    c = sqlite3.connect(lf.DB_PATH)
    clear(c)
    if "--clear" in sys.argv:
        c.commit(); print("Mock data removed."); return

    subprocess.run([sys.executable, "build.py"], cwd=SEED, check=True)
    subprocess.run([sys.executable, "draw.py"], cwd=SEED, check=True)
    items = json.load(open(os.path.join(SEED, "items_draft.json")))
    used = {t for (t,) in c.execute("SELECT tag FROM items")}
    by_title = {}
    for it in items:
        names = []
        n = it.get("photo_n")
        for suffix in (["a", "b"] if it.get("closeup") else ["a"]) if n else []:
            name = uuid.uuid4().hex + ".jpg"
            shutil.copy(os.path.join(SEED, "photos", f"p{n:02d}{suffix}.jpg"), os.path.join(lf.PHOTO_DIR, name))
            names.append(name)
        if it["tag"] in used:
            continue
        item_id = uuid.uuid4().hex[:12]
        c.execute("""INSERT INTO items (id, tag, title, category, color, brand, description, keywords, photos, location,
                     found_where, found_at, status, returned_at, mock) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                  (item_id, it["tag"], it["title"], it["category"], it["color"], it["brand"], it["description"],
                   json.dumps(it["keywords"]), json.dumps(names), it["location"], it["foundWhere"], it["foundAt"],
                   it["status"], it.get("returnedAt")))
        by_title[it["title"]] = item_id

    now = int(time.time() * 1000)
    claims = [
        ("ava.r@example.org", "Light blue Hydro Flask with soccer sticker", "Ava R.", "7th, Room 214",
         "It has a soccer ball sticker and a dent on the bottom from when I dropped it at practice."),
        ("ethan.p@example.org", "Navy Nike hoodie, size M", "Ethan P.", "6th, Room 108",
         "Youth medium. I left a yellow pencil in the front pocket."),
        ("jayden.m@example.org", "TI-84 Plus CE calculator", "Jayden M.", "8th, Room 301",
         "My initials J.M. are on the back in white marker."),
        ("liam.k@example.org", "Navy Nike hoodie, size M", "Liam K.", "6th, Room 110", "It's navy and says Nike on it."),
    ]
    for k, (email, title, name, grade, proof) in enumerate(claims):
        c.execute("""INSERT INTO claims (item_id, student_email, name, grade, proof, created_at, mock)
                     VALUES (?,?,?,?,?,?,1)""", (by_title[title], email, name, grade, proof, now - (k + 1) * 3600000))
    c.commit()
    print(f"Loaded {len(by_title)} mock items and {len(claims)} claims.")

if __name__ == "__main__":
    main()
