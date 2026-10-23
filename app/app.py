"""Lost & Found Desk: a school lost-and-found app.

Flask + Google sign-in + Claude API. One file on purpose.
Storage: SQLite + a photo folder on your computer; Postgres + Vercel Blob when deployed on Vercel.
Run:  python app.py      (reads settings from .env, see .env.example)
"""
import base64, io, json, os, re, secrets, sqlite3, sys, time, uuid
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, Response, abort, g, jsonify, redirect, request, send_from_directory, session, url_for
from PIL import Image, ImageOps

load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)   # so `import demo` works wherever the app is started from
PUBLIC_DIR = os.path.join(os.path.dirname(HERE), "public")   # the page, its script and the help page
ON_VERCEL = os.environ.get("VERCEL") == "1"

# Database: Postgres when DATABASE_URL (or POSTGRES_URL) is set, otherwise a local SQLite file.
# Neon on Vercel names it DATABASE_URL by default; STORAGE_URL / POSTGRES_URL cover other prefixes people pick.
DATABASE_URL = (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or os.environ.get("STORAGE_URL") or "")
USE_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
# Photos: a private Vercel Blob store when one is connected, otherwise a local folder.
USE_BLOB = bool(os.environ.get("BLOB_READ_WRITE_TOKEN") or os.environ.get("BLOB_STORE_ID"))
BLOB_ACCESS = os.environ.get("BLOB_ACCESS", "private")

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(HERE, "data"))
PHOTO_DIR = os.path.join(DATA_DIR, "photos")
DB_PATH = os.path.join(DATA_DIR, "lostfound.db")
if not ON_VERCEL:
    os.makedirs(PHOTO_DIR, exist_ok=True)

# Vercel's disk is read-only and every request may land on a different server, so these are required there.
CONFIG_PROBLEMS = []
if ON_VERCEL:
    if not USE_PG:
        CONFIG_PROBLEMS.append("Connect a Postgres database (project Storage tab, Neon). It sets DATABASE_URL.")
    if not USE_BLOB:
        CONFIG_PROBLEMS.append("Connect a private Blob store (project Storage tab, Blob). It sets BLOB_STORE_ID.")

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

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    MAX_CONTENT_LENGTH=20 * 1024 * 1024,   # Vercel caps a request at 4.5 MB; photos are shrunk in the browser first
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=ON_VERCEL or (os.environ.get("HTTPS", "1") == "1" and not DEV_LOGIN),
)

@app.before_request
def config_check():
    if CONFIG_PROBLEMS:
        items = "".join(f"<li>{p}</li>" for p in CONFIG_PROBLEMS)
        return (f"<h1>Lost &amp; Found Desk isn't set up yet</h1><ul>{items}</ul>"
                "<p>Fix these in the Vercel project settings, then redeploy.</p>"), 503

# ---------------------------------------------------------------- database
# Same tables in both databases. {ID} and {BIG} are filled in per database.
SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY, tag TEXT UNIQUE, title TEXT, category TEXT, color TEXT, brand TEXT,
  description TEXT, keywords TEXT DEFAULT '[]', photos TEXT DEFAULT '[]',
  location TEXT, found_where TEXT, found_at {BIG}, status TEXT DEFAULT 'available',
  returned_at {BIG}, returned_to TEXT, logged_by TEXT, mock INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS claims (
  id {ID}, item_id TEXT, student_email TEXT, name TEXT, grade TEXT,
  proof TEXT, status TEXT DEFAULT 'pending', note TEXT, created_at {BIG}, decided_at {BIG},
  mock INTEGER DEFAULT 0, UNIQUE(item_id, student_email));
CREATE TABLE IF NOT EXISTS ai_usage (email TEXT, day TEXT, count INTEGER DEFAULT 0, PRIMARY KEY (email, day));
CREATE TABLE IF NOT EXISTS app_settings (name TEXT PRIMARY KEY, value TEXT)
"""

if USE_PG:
    import psycopg
    from psycopg.rows import dict_row
    DUPLICATE_ERRORS = (sqlite3.IntegrityError, psycopg.IntegrityError)
else:
    DUPLICATE_ERRORS = (sqlite3.IntegrityError,)

class Postgres:
    """Gives a Postgres connection the same small interface as sqlite3, so the queries below work on both."""
    def __init__(self):
        self.conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    def execute(self, sql, params=()):
        return self.conn.execute(sql.replace("?", "%s"), params)
    def executemany(self, sql, rows):
        with self.conn.cursor() as cur:
            cur.executemany(sql.replace("?", "%s"), rows)
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self): self.conn.close()

def connect():
    if USE_PG:
        return Postgres()
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def db():
    if "db" not in g:
        g.db = connect()
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    if CONFIG_PROBLEMS:
        return
    schema = SCHEMA.format(ID="BIGSERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT",
                           BIG="BIGINT" if USE_PG else "INTEGER")
    c = connect()
    try:
        for stmt in schema.split(";"):
            if stmt.strip():
                c.execute(stmt)
        c.commit()
    finally:
        c.close()

def load_secret_key():
    """The key that signs login cookies. SECRET_KEY wins if set; otherwise the app makes one on first start
    and keeps it in the database, so every server and every restart signs cookies the same way."""
    if os.environ.get("SECRET_KEY") or CONFIG_PROBLEMS:
        return
    c = connect()
    try:
        c.execute("INSERT INTO app_settings (name, value) VALUES (?, ?) ON CONFLICT (name) DO NOTHING",
                  ("secret_key", secrets.token_hex(32)))
        c.commit()
        app.secret_key = c.execute("SELECT value FROM app_settings WHERE name=?", ("secret_key",)).fetchone()["value"]
    finally:
        c.close()

def row_values(r):
    return list(r.values()) if isinstance(r, dict) else list(r)

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

STOP = set("""a an the my i is it was with and or of in on at to for near lost found have has had its that this
from some kind sort i'm im me left think maybe like color colour one has looks""".split())

# Words students use for the same kind of thing. Searching any word in a group also matches the others,
# so "sweatshirt" finds an item a staff member typed in as "hoodie". Add your school's words here.
SYNONYM_GROUPS = [
    "hoodie sweatshirt pullover sweater jumper fleece jacket coat zipup zip-up cardigan windbreaker puffer",
    "bottle flask hydroflask hydro tumbler stanley owala yeti nalgene contigo camelbak cup",
    "backpack bookbag knapsack bag drawstring tote duffel",
    "lunchbox lunch bento bentgo thermos",
    "calculator calc ti-84 ti84 graphing scientific casio",
    "earbuds airpods earphones earpods headphones headset beats",
    "glasses eyeglasses spectacles specs frames sunglasses shades",
    "hat cap beanie",
    "shoe shoes sneaker sneakers cleats trainers",
    "charger cable cord",
    "notebook binder folder journal composition sketchbook",
    "keys key keychain lanyard id badge",
    "ball soccer basketball volleyball football",
    "pencil pen pencils pens pouch",
    "navy dark-blue",
    "grey gray",
]
SYNONYMS = {}
for _g in SYNONYM_GROUPS:
    _words = _g.split()
    for _w in _words:
        SYNONYMS.setdefault(_w, set()).update(_words)

def _word_in(word, hay):
    return re.search(r"(?<![a-z0-9])" + re.escape(word), hay) is not None  # matches at the start of a word

def keyword_search(q, items):
    """Free search: synonym-aware word matching. Item-type words (hoodie, bottle) count double so they
    outrank color words (blue)."""
    q = q.lower().replace("dark blue", "dark-blue").replace("zip up", "zip-up")
    toks = [t for t in re.split(r"[^a-z0-9\-]+", q) if len(t) > 1 and t not in STOP]
    toks = list(dict.fromkeys(toks))
    if not toks:
        return []
    weights = {t: 2 if t in SYNONYMS and t not in ("navy", "dark-blue", "grey", "gray") else 1 for t in toks}
    total = sum(weights.values())
    out = []
    for it in items:
        hay = " ".join([it["title"] or "", it["category"] or "", it["color"] or "", it["brand"] or "",
                        it["description"] or "", " ".join(json.loads(it["keywords"] or "[]")), it["found_where"] or ""]).lower()
        hits, s = [], 0.0
        for t in toks:
            exact = {t, t[:-1]} if t.endswith("s") and len(t) > 3 else {t}
            if any(_word_in(a, hay) for a in exact):
                hits.append(t); s += weights[t]            # the student's own word: full credit
            elif any(_word_in(a, hay) for a in SYNONYMS.get(t, ())):
                hits.append(t); s += weights[t] * 0.6      # a synonym: partial credit, so exact words rank first
        if hits:
            s = s / total
            out.append((s, it["found_at"] or 0, it["id"], hits))
    out.sort(key=lambda x: (-x[0], -x[1]))
    if out and out[0][0] >= .5:  # a strong match exists: drop items that only share a minor word like "blue"
        out = [o for o in out if o[0] >= .34]
    return [{"id": i, "confidence": "high" if s >= .7 else "medium" if s >= .4 else "low",
             "reason": "Matches: " + ", ".join(h[:5])} for s, _, i, h in out[:8]]

# ---------------------------------------------------------------- pages & photos
# On Vercel these files are served straight from public/ (see vercel.json); these routes cover local runs.
@app.get("/")
def index():
    return send_from_directory(PUBLIC_DIR, "index.html")

@app.get("/help")
def help_page():
    return send_from_directory(PUBLIC_DIR, "help.html")

@app.get("/<any('app.js', 'help.html', 'index.html'):name>")
def public_file(name):
    return send_from_directory(PUBLIC_DIR, name)

# ---- photo storage: Vercel Blob when connected, else the local photos folder
def store_photo(name, data):
    if USE_BLOB:
        from vercel.blob import sync as blob
        blob.put_blob(f"photos/{name}", data, access=BLOB_ACCESS, content_type="image/jpeg", allow_overwrite=True)
    else:
        with open(os.path.join(PHOTO_DIR, name), "wb") as f:
            f.write(data)

def remove_photo(name):
    try:
        if USE_BLOB:
            from vercel.blob import sync as blob
            blob.delete_blob(f"photos/{name}")
        else:
            os.remove(os.path.join(PHOTO_DIR, name))
    except Exception:
        pass  # a photo that's already gone is fine

@app.get("/photos/<name>")
def photo(name):
    if "email" not in session:
        abort(401)
    if not re.fullmatch(r"[0-9a-f]{32}\.jpg", name):
        abort(404)
    if not USE_BLOB:
        return send_from_directory(PHOTO_DIR, name, max_age=86400)
    from vercel.blob import sync as blob
    try:
        body = blob.get_blob(f"photos/{name}", access=BLOB_ACCESS).body
    except blob.BlobNotFoundError:
        abort(404)
    # names are random and never reused, so the browser may keep its copy for a day
    return Response(body, mimetype="image/jpeg",
                    headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})

def save_photo(file_storage):
    """Re-encode every upload: fixes rotation, shrinks it, and strips EXIF (including phone GPS)."""
    img = ImageOps.exif_transpose(Image.open(file_storage.stream)).convert("RGB")
    img.thumbnail((1600, 1600))
    name = uuid.uuid4().hex + ".jpg"
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    store_photo(name, buf.getvalue())
    return name, buf.getvalue()

# ---------------------------------------------------------------- API
@app.get("/api/me")
def me():
    if "email" not in session:
        return jsonify(signedIn=False, devLogin=DEV_LOGIN, googleLogin=bool(oauth))
    return jsonify(signedIn=True, email=session["email"], name=session["name"], role=session["role"],
                   ai=bool(claude()), categories=CATEGORIES, demo=DEV_LOGIN)

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
            remove_photo(p)
        db().execute("DELETE FROM claims WHERE item_id=?", (item_id,))
        db().execute("DELETE FROM items WHERE id=?", (item_id,))
        db().commit()
    return jsonify(ok=True)

AI_SEARCHES_PER_DAY = int(os.environ.get("AI_SEARCHES_PER_DAY", "20"))  # per student; staff aren't limited
_ai_cache = {}  # (normalized query, shelf version) -> matches. Repeat AI searches cost nothing.

def normalize_query(q):
    return " ".join(sorted(set(t for t in re.split(r"[^a-z0-9\-]+", q.lower()) if len(t) > 1 and t not in STOP)))

def shelf_version():
    """Changes whenever an item is added, removed, returned or put back, so cached AI answers stay correct."""
    r = db().execute("SELECT COUNT(*) AS n, COALESCE(MAX(found_at),0) AS newest, "
                     "COALESCE(SUM(CASE WHEN status='returned' THEN 1 ELSE 0 END),0) AS returned, "
                     "COALESCE(MAX(returned_at),0) AS last_return FROM items").fetchone()
    return ":".join(str(x) for x in row_values(r))

def ai_searches_used_today(email):
    r = db().execute("SELECT count FROM ai_usage WHERE email=? AND day=?", (email, time.strftime("%Y-%m-%d"))).fetchone()
    return r["count"] if r else 0

def count_ai_search(email):
    db().execute("""INSERT INTO ai_usage (email, day, count) VALUES (?,?,1)
                    ON CONFLICT(email, day) DO UPDATE SET count = ai_usage.count + 1""", (email, time.strftime("%Y-%m-%d")))
    db().commit()

def ai_left():
    return None if is_staff() else max(0, AI_SEARCHES_PER_DAY - ai_searches_used_today(session["email"]))

@app.post("/api/search")
@signed_in()
def search():
    """Keyword search by default (free). With {"ai": true}, Claude searches the whole shelf, on request only."""
    body = request.get_json(force=True)
    q = (body.get("q") or "").strip()[:800]
    use_ai = bool(body.get("ai"))
    items = db().execute("SELECT * FROM items WHERE status='available' ORDER BY found_at DESC LIMIT 300").fetchall()
    base = {"aiAvailable": bool(claude()), "aiLeft": ai_left() if claude() else 0}
    if not q or not items:
        return jsonify(matches=[], note="", mode="keyword", **base)
    if not use_ai or not claude():
        return jsonify(matches=keyword_search(q, items), note="Word matches", mode="keyword", **base)

    key = (normalize_query(q), shelf_version())
    if key in _ai_cache:
        return jsonify(matches=_ai_cache[key], note="Matched by AI from your description", mode="ai", **base)
    if base["aiLeft"] == 0:
        return jsonify(error=f"You've used today's {AI_SEARCHES_PER_DAY} AI searches. Try again tomorrow, or ask the office."), 429

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
    except Exception:
        return jsonify(error="AI search isn't working right now. Try again in a minute."), 502
    ids = {r["id"] for r in items}
    matches = [{"id": str(m["id"]), "confidence": m.get("confidence") if m.get("confidence") in ("high", "medium", "low") else "low",
                "reason": str(m.get("reason", ""))[:220]} for m in out.get("matches", []) if str(m.get("id")) in ids][:8]
    if len(_ai_cache) > 500:
        _ai_cache.clear()
    _ai_cache[key] = matches
    if not is_staff():
        count_ai_search(session["email"])
    base["aiLeft"] = ai_left()
    return jsonify(matches=matches, note="Matched by AI from your description", mode="ai", **base)

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
    except DUPLICATE_ERRORS:
        db().rollback()
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

# ---------------------------------------------------------------- demo data (test mode only)
@app.post("/api/demo/reset")
@signed_in(staff=True)
def demo_reset():
    """Replace the demo items and claims with a fresh set. Items staff logged themselves stay."""
    if not DEV_LOGIN:
        abort(404)
    import demo
    n_items, n_claims = demo.load(db(), store_photo, remove_photo)
    _ai_cache.clear()
    return jsonify(items=n_items, claims=n_claims)

init_db()
load_secret_key()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=DEV_LOGIN)
