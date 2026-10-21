"""Lost & Found Desk: a school lost-and-found app.

Flask + SQLite + Google sign-in + Claude API. One file on purpose.
Run:  python app.py      (reads settings from .env, see .env.example)
"""
import base64, io, json, os, re, secrets, sqlite3, time, uuid
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, abort, g, jsonify, redirect, request, send_from_directory, session, url_for
from PIL import Image, ImageOps

load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(HERE, "data"))
PHOTO_DIR = os.path.join(DATA_DIR, "photos")
DB_PATH = os.path.join(DATA_DIR, "lostfound.db")
os.makedirs(PHOTO_DIR, exist_ok=True)

def env_list(name):
    return [x.strip().lower() for x in os.environ.get(name, "").split(",") if x.strip()]

ALLOWED_DOMAINS = env_list("ALLOWED_DOMAINS")     # e.g. district.org,students.district.org
STAFF_EMAILS = set(env_list("STAFF_EMAILS"))      # who gets the office tools
DEV_LOGIN = os.environ.get("DEV_LOGIN") == "1"    # local testing without Google; never in production
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5")
DAY = 86400000

CATEGORIES = ["Water bottle", "Jacket / hoodie", "Other clothing", "Backpack / bag", "Lunch box", "Electronics",
              "Calculator", "Book / notebook", "School supplies", "Sports gear", "Glasses", "Jewelry / accessory",
              "Keys / ID", "Other"]

app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    MAX_CONTENT_LENGTH=40 * 1024 * 1024,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.environ.get("HTTPS", "1") == "1" and not DEV_LOGIN,
)

# ---------------------------------------------------------------- database
SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY, tag TEXT UNIQUE, title TEXT, category TEXT, color TEXT, brand TEXT,
  description TEXT, keywords TEXT DEFAULT '[]', photos TEXT DEFAULT '[]',
  location TEXT, found_where TEXT, found_at INTEGER, status TEXT DEFAULT 'available',
  returned_at INTEGER, returned_to TEXT, logged_by TEXT, mock INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS claims (
  id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, student_email TEXT, name TEXT, grade TEXT,
  proof TEXT, status TEXT DEFAULT 'pending', note TEXT, created_at INTEGER, decided_at INTEGER,
  mock INTEGER DEFAULT 0, UNIQUE(item_id, student_email));
"""

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.executescript(SCHEMA)

def now_ms():
    return int(time.time() * 1000)

def item_json(r, staff):
    d = dict(r)
    d["keywords"] = json.loads(d["keywords"] or "[]")
    d["photos"] = [f"/photos/{p}" for p in json.loads(d["photos"] or "[]")]
    d.pop("mock", None)
    if not staff:  # students never see where an item is kept or who logged it
        for k in ("location", "logged_by", "returned_to"):
            d.pop(k, None)
    return d

def new_tag():
    while True:
        t = f"LF-{secrets.randbelow(9000) + 1000}"
        if not db().execute("SELECT 1 FROM items WHERE tag=?", (t,)).fetchone():
            return t

# ---------------------------------------------------------------- auth
oauth = None
if os.environ.get("GOOGLE_CLIENT_ID"):
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(app)
    oauth.register(
        name="google",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

def email_allowed(email, hd):
    if not ALLOWED_DOMAINS:
        return True
    domain = email.rsplit("@", 1)[-1].lower()
    # `hd` is set by Google only for Workspace (school-managed) accounts, so a personal gmail can't pass
    return domain in ALLOWED_DOMAINS and (hd or "").lower() == domain

def start_session(email, name):
    email = email.lower()
    session.clear()
    session.update(email=email, name=name or email.split("@")[0], role="staff" if email in STAFF_EMAILS else "student")
    session.permanent = True

@app.get("/login")
def login():
    if not oauth:
        return "Google sign-in isn't set up. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env.", 500
    hint = {"hd": ALLOWED_DOMAINS[0]} if len(ALLOWED_DOMAINS) == 1 else {}  # shows only school accounts in the picker
    return oauth.google.authorize_redirect(url_for("auth_callback", _external=True), prompt="select_account", **hint)

@app.get("/auth/callback")
def auth_callback():
    token = oauth.google.authorize_access_token()
    info = token.get("userinfo") or {}
    email = info.get("email", "")
    if not info.get("email_verified") or not email_allowed(email, info.get("hd")):
        session.clear()
        return redirect("/?error=domain")
    start_session(email, info.get("name"))
    return redirect("/")

@app.get("/dev-login")
def dev_login():
    if not DEV_LOGIN:
        abort(404)
    email = request.args.get("email", "office@example.org")
    start_session(email, request.args.get("name") or email.split("@")[0].replace(".", " ").title())
    if request.args.get("role") in ("staff", "student"):
        session["role"] = request.args["role"]
    return redirect("/")

@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")

def signed_in(staff=False):
    def wrap(fn):
        @wraps(fn)
        def inner(*a, **kw):
            if "email" not in session:
                return jsonify(error="Sign in first."), 401
            if staff and session.get("role") != "staff":
                return jsonify(error="Only office staff can do that."), 403
            # simple CSRF guard: browsers won't send this header cross-site without CORS
            if request.method != "GET" and request.headers.get("X-Requested-With") != "fetch":
                return jsonify(error="Bad request."), 400
            return fn(*a, **kw)
        return inner
    return wrap

def is_staff():
    return session.get("role") == "staff"

# ---------------------------------------------------------------- AI (Claude)
_claude = None
def claude():
    global _claude
    if _claude is None and os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        _claude = anthropic.Anthropic()
    return _claude

def ask_claude_json(prompt, images=()):
    """Send a prompt (plus optional JPEG bytes) to Claude and parse a JSON reply."""
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                            "data": base64.b64encode(b).decode()}} for b in images]
    content.append({"type": "text", "text": prompt + "\nReply with only the JSON, no other text."})
    msg = claude().messages.create(model=CLAUDE_MODEL, max_tokens=1500, messages=[{"role": "user", "content": content}])
    text = "".join(b.text for b in msg.content if b.type == "text")
    m = re.search(r"[\[{].*[\]}]", text, re.S)
    return json.loads(m.group(0) if m else text)

DESCRIBE_PROMPT = f"""These photos show ONE item turned in to a school lost and found. Catalog it so a student can find it
later by describing it in their own words. JSON shape:
{{"title": "short name, at most 6 words, e.g. Navy Nike zip-up hoodie",
 "category": one of {json.dumps(CATEGORIES)},
 "color": "main color(s)", "brand": "brand if visible, else empty string",
 "description": "1-2 sentences of distinguishing details: stickers, writing, damage, size, what's inside",
 "keywords": ["8 to 14 lowercase words a student might use, including synonyms, e.g. hoodie, sweatshirt, jacket"]}}"""

STOP = set("a an the my i is it was with and or of in on at to for near lost found have has had its that this from some kind sort".split())

def keyword_search(q, items):
    toks = [t for t in re.split(r"[^a-z0-9]+", q.lower()) if len(t) > 1 and t not in STOP]
    out = []
    for it in items:
        hay = " ".join([it["title"] or "", it["category"] or "", it["color"] or "", it["brand"] or "",
                        it["description"] or "", " ".join(json.loads(it["keywords"] or "[]")), it["found_where"] or ""]).lower()
        hits = [t for t in toks if t in hay or (t.endswith("s") and t[:-1] in hay)]
        if hits:
            s = len(hits) / max(len(toks), 1)
            out.append((s, it["id"], "high" if s >= .6 else "medium" if s >= .3 else "low", "Matches: " + ", ".join(hits[:5])))
    out.sort(key=lambda x: -x[0])
    if out and out[0][0] >= .5:  # a strong match exists: drop items that only share one word like "blue"
        out = [o for o in out if o[0] >= .3]
    return [{"id": i, "confidence": c, "reason": r} for _, i, c, r in out[:8]]

# ---------------------------------------------------------------- pages & photos
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.get("/photos/<name>")
def photo(name):
    if "email" not in session:
        abort(401)
    if not re.fullmatch(r"[0-9a-f]{32}\.jpg", name):
        abort(404)
    return send_from_directory(PHOTO_DIR, name, max_age=86400)

def save_photo(file_storage):
    """Re-encode every upload: fixes rotation, shrinks it, and strips EXIF (including phone GPS)."""
    img = ImageOps.exif_transpose(Image.open(file_storage.stream)).convert("RGB")
    img.thumbnail((1600, 1600))
    name = uuid.uuid4().hex + ".jpg"
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    with open(os.path.join(PHOTO_DIR, name), "wb") as f:
        f.write(buf.getvalue())
    return name, buf.getvalue()

# ---------------------------------------------------------------- API
@app.get("/api/me")
def me():
    if "email" not in session:
        return jsonify(signedIn=False, devLogin=DEV_LOGIN, googleLogin=bool(oauth))
    return jsonify(signedIn=True, email=session["email"], name=session["name"], role=session["role"],
                   ai=bool(claude()), categories=CATEGORIES)

@app.get("/api/items")
@signed_in()
def list_items():
    q = "SELECT * FROM items ORDER BY found_at DESC" if is_staff() else \
        "SELECT * FROM items WHERE status='available' ORDER BY found_at DESC"
    return jsonify([item_json(r, is_staff()) for r in db().execute(q)])

@app.post("/api/describe")
@signed_in(staff=True)
def describe():
    if not claude():
        return jsonify(error="AI isn't set up. Add ANTHROPIC_API_KEY to .env, or type the details."), 503
    images = []
    for f in request.files.getlist("photos")[:3]:
        img = ImageOps.exif_transpose(Image.open(f.stream)).convert("RGB")
        img.thumbnail((1200, 1200))
        b = io.BytesIO(); img.save(b, "JPEG", quality=80); images.append(b.getvalue())
    if not images:
        return jsonify(error="Add at least one photo."), 400
    try:
        out = ask_claude_json(DESCRIBE_PROMPT, images)
    except Exception:
        return jsonify(error="AI couldn't read the photos this time. Type the details instead."), 502
    if out.get("category") not in CATEGORIES:
        out["category"] = "Other"
    return jsonify(out)

@app.post("/api/items")
@signed_in(staff=True)
def create_item():
    f = request.form
    files = request.files.getlist("photos")[:3]
    if not files:
        return jsonify(error="Add at least one photo."), 400
    if not f.get("location", "").strip():
        return jsonify(error="Say where you're storing it."), 400
    if not f.get("title", "").strip():
        return jsonify(error="Give the item a name."), 400
    names = [save_photo(x)[0] for x in files]
    item_id, tag = uuid.uuid4().hex[:12], new_tag()
    kw = json.loads(f.get("keywords") or "[]")
    db().execute("""INSERT INTO items (id, tag, title, category, color, brand, description, keywords, photos,
                    location, found_where, found_at, status, logged_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'available', ?)""",
                 (item_id, tag, f["title"].strip()[:120], f.get("category", "Other"), f.get("color", "")[:80],
                  f.get("brand", "")[:80], f.get("description", "")[:1000], json.dumps([str(k)[:40] for k in kw][:16]),
                  json.dumps(names), f["location"].strip()[:120], f.get("found_where", "")[:120], now_ms(), session["email"]))
    db().commit()
    return jsonify(id=item_id, tag=tag)

@app.patch("/api/items/<item_id>")
@signed_in(staff=True)
def update_item(item_id):
    body = request.get_json(force=True)
    if "location" in body and body["location"].strip():
        db().execute("UPDATE items SET location=? WHERE id=?", (body["location"].strip()[:120], item_id))
    if body.get("status") == "returned":
        db().execute("UPDATE items SET status='returned', returned_at=? WHERE id=?", (now_ms(), item_id))
    elif body.get("status") == "available":
        db().execute("UPDATE items SET status='available', returned_at=NULL, returned_to=NULL WHERE id=?", (item_id,))
    db().commit()
    return jsonify(ok=True)

@app.delete("/api/items/<item_id>")
@signed_in(staff=True)
def delete_item(item_id):
    r = db().execute("SELECT photos FROM items WHERE id=?", (item_id,)).fetchone()
    if r:
        for p in json.loads(r["photos"] or "[]"):
            try: os.remove(os.path.join(PHOTO_DIR, p))
            except OSError: pass
        db().execute("DELETE FROM claims WHERE item_id=?", (item_id,))
        db().execute("DELETE FROM items WHERE id=?", (item_id,))
        db().commit()
    return jsonify(ok=True)

@app.post("/api/search")
@signed_in()
def search():
    q = (request.get_json(force=True).get("q") or "").strip()[:800]
    items = db().execute("SELECT * FROM items WHERE status='available' ORDER BY found_at DESC LIMIT 300").fetchall()
    if not q or not items:
        return jsonify(matches=[], note="")
    if claude():
        catalog = [{"id": r["id"], "title": r["title"], "category": r["category"], "color": r["color"], "brand": r["brand"],
                    "details": (r["description"] or "")[:280], "keywords": json.loads(r["keywords"] or "[]")[:14],
                    "found_where": r["found_where"], "found_on": time.strftime("%Y-%m-%d", time.localtime(r["found_at"] / 1000))}
                   for r in items]
        prompt = f'''A student is looking for something they lost at school. Their description:
"""{q}"""
Items currently in the lost and found (JSON):
{json.dumps(catalog)}
Pick the items that could plausibly be theirs, best first, at most 6. Treat synonyms as matches
(hoodie ~ sweatshirt, bottle ~ Hydro Flask, calculator ~ TI-84). Weigh item type first, then color, brand and details.
Leave out items of a clearly different type or color.
JSON shape: {{"matches": [{{"id": "item id", "confidence": "high|medium|low", "reason": "one short sentence to the student"}}]}}
Use an empty list if nothing fits.'''
        try:
            out = ask_claude_json(prompt)
            ids = {r["id"] for r in items}
            matches = [{"id": str(m["id"]), "confidence": m.get("confidence") if m.get("confidence") in ("high", "medium", "low") else "low",
                        "reason": str(m.get("reason", ""))[:220]} for m in out.get("matches", []) if str(m.get("id")) in ids][:8]
            return jsonify(matches=matches, note="Matched by AI from your description")
        except Exception:
            return jsonify(matches=keyword_search(q, items), note="AI couldn't answer this time. These are keyword matches.")
    return jsonify(matches=keyword_search(q, items), note="Keyword matches")

@app.get("/api/claims/mine")
@signed_in()
def my_claims():
    rows = db().execute("""SELECT c.*, i.tag, i.title, i.photos FROM claims c JOIN items i ON i.id=c.item_id
                           WHERE c.student_email=? ORDER BY c.created_at DESC""", (session["email"],))
    return jsonify([claim_json(r) for r in rows])

@app.post("/api/claims")
@signed_in()
def create_claim():
    b = request.get_json(force=True)
    it = db().execute("SELECT * FROM items WHERE id=? AND status='available'", (b.get("item_id"),)).fetchone()
    if not it:
        return jsonify(error="That item isn't available any more."), 404
    name, proof = (b.get("name") or "").strip(), (b.get("proof") or "").strip()
    if not name or not proof:
        return jsonify(error="Fill in your name and how the office can tell it's yours."), 400
    try:
        db().execute("""INSERT INTO claims (item_id, student_email, name, grade, proof, created_at) VALUES (?,?,?,?,?,?)""",
                     (it["id"], session["email"], name[:80], (b.get("grade") or "")[:60], proof[:600], now_ms()))
        db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error="You already claimed this item."), 409
    return jsonify(ok=True)

@app.get("/api/claims")
@signed_in(staff=True)
def all_claims():
    rows = db().execute("""SELECT c.*, i.tag, i.title, i.photos, i.description, i.location, i.status AS item_status
                           FROM claims c JOIN items i ON i.id=c.item_id
                           ORDER BY (c.status='pending') DESC, c.created_at DESC LIMIT 200""")
    return jsonify([claim_json(r, staff=True) for r in rows])

def claim_json(r, staff=False):
    d = {k: r[k] for k in ("id", "item_id", "name", "grade", "proof", "status", "note", "created_at", "decided_at", "tag", "title")}
    photos = json.loads(r["photos"] or "[]")
    d["photo"] = f"/photos/{photos[0]}" if photos else None
    if staff:
        d.update(email=r["student_email"], item_description=r["description"], location=r["location"], item_status=r["item_status"])
    return d

@app.post("/api/claims/<int:claim_id>/decide")
@signed_in(staff=True)
def decide(claim_id):
    approve = bool(request.get_json(force=True).get("approve"))
    c = db().execute("SELECT * FROM claims WHERE id=? AND status='pending'", (claim_id,)).fetchone()
    if not c:
        return jsonify(error="That claim was already decided."), 404
    t = now_ms()
    if approve:
        db().execute("UPDATE claims SET status='approved', decided_at=? WHERE id=?", (t, claim_id))
        db().execute("UPDATE items SET status='returned', returned_at=?, returned_to=? WHERE id=?", (t, c["student_email"], c["item_id"]))
        db().execute("""UPDATE claims SET status='declined', decided_at=?, note='It was returned to its owner'
                        WHERE item_id=? AND id<>? AND status='pending'""", (t, c["item_id"], claim_id))
    else:
        db().execute("UPDATE claims SET status='declined', decided_at=? WHERE id=?", (t, claim_id))
    db().commit()
    return jsonify(ok=True)

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=DEV_LOGIN)
