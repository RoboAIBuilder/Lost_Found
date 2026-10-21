# Lost & Found Desk

A school lost-and-found app.

- **Office staff** take 2–3 photos of a found item and say where it's stored. AI reads the photos and writes the description.
- **Students** sign in with their school Google account and describe what they lost in plain English. A free word search runs first; if their item isn't there, **Search with AI** checks every item on the shelf. They tap **This is mine** to claim it.
- **Staff** compare each claim with the photos and approve or decline it. Approving marks the item returned and declines any other claims on it.

The repo has two versions of the same app:

| Folder | What it is |
|---|---|
| `app/` | **The school version.** Python (Flask) + SQLite + Google sign-in + Claude API. Runs on any server. |
| `artifact.html` | The prototype, which runs only inside Claude as an Artifact. |
| `seed/` | Scripts that generate 121 mock middle-school items with drawn photos, for demos. |
| `docs/pitch.html` | One-page pitch: features, AI cost, privacy and where it fits. Open it in a browser. |

**User guide:** the app has a built-in **How it works** page at `/help`, linked from the header and the sign-in screen. It covers finding and claiming an item, logging items, reviewing claims, and common questions.

---

## Run it on your computer (5 minutes, no Google setup)

Needs Python 3.10+.

```bash
cd app
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```

Edit `.env` and set:

```
DEV_LOGIN=1
STAFF_EMAILS=office@example.org
ANTHROPIC_API_KEY=sk-ant-...       # optional, turns on AI
```

Load the demo data and start it:

```bash
python seed_mock.py
python app.py
```

Open http://localhost:5000. Test mode shows **Office staff**, **Student: Ava** and **Student: Liam** buttons instead of Google sign-in. Use a private window to be staff and a student at the same time.

Without `ANTHROPIC_API_KEY`, everything still works, except that the **Search with AI** button is hidden and staff type item details by hand.

`python seed_mock.py --clear` removes only the demo data.

---

## How search keeps AI costs low

AI is used only where it adds something:

| Step | AI calls |
|---|---|
| Staff log an item | **1**, after the last photo is added. Adding or removing photos doesn't call AI again; staff can click "Read the photos again" if needed. |
| Student searches | **0**. Free word search runs first. |
| Student clicks **Search with AI** | **1**, only when they ask. The same search on an unchanged shelf reuses the earlier answer at no cost. |

**How word search works.** It matches the student's words against each item's name, color, brand, details, keywords and where it was found.
- **Synonyms:** "sweatshirt" also finds "hoodie", and "specs" finds "glasses". Add your school's words to `SYNONYM_GROUPS` in `app.py`.
- **Ranking:** the student's own words count more than synonyms, and item-type words like "hoodie" count more than colors like "blue".

**Guardrails:**
- Each student gets `AI_SEARCHES_PER_DAY` AI searches a day (default 20). Staff have no limit.
- Set a monthly spend limit in the Anthropic Console as a hard cap.

**What it costs** (estimates, Claude Haiku 5.5 at $0.10 per million input tokens and $0.50 per million output):

| | Cost |
|---|---|
| Word search | $0 |
| AI search, about 110 items on the shelf | about $0.001 |
| Photo description, 2 photos | about $0.0004 |
| **Typical school a month**: 1,000 searches, 60 new items, word search finds 85% | **about $0.16** (vs $1.17 if every search used AI) |
| **Large college a month**: 10,000 searches, 300 items on the shelf | **about $3.50** (vs about $28) |

---

## How sign-in works with the school's Google accounts

Students already sign in to Chromebooks and Classroom with a school Google Workspace account, like `ava.r@students.district.org`. This app uses that same account through **Sign in with Google**. There are no new passwords and no accounts to create.

1. A student clicks **Sign in with Google** and picks their school account. If they're already signed in on a Chromebook, it's one click.
2. Google sends back their verified email, name and the Workspace domain (`hd`).
3. The app lets them in only if the email domain is in `ALLOWED_DOMAINS` **and** Google confirms it's a school-managed Workspace account. Personal Gmail accounts are refused.
4. Emails in `STAFF_EMAILS` get the office tools. Everyone else is a student.

The app asks Google only for basic profile info (`openid email profile`). It never touches Drive, Gmail or Classroom.

### Set up Google sign-in (school or district IT does this once)

1. **Create the project inside the school's Google Workspace.** Sign in to [console.cloud.google.com](https://console.cloud.google.com) with a school admin account and create a project, e.g. "Lost and Found".
2. **Configure the consent screen.** Go to **APIs & Services → OAuth consent screen**, choose **Internal**, and enter the app name and support email.
   - **Internal** means only accounts in the school's Workspace can sign in, and Google doesn't require app verification.
3. **Create the client ID.** Go to **APIs & Services → Credentials → Create credentials → OAuth client ID**, choose **Web application**, and add these authorized redirect URIs:
   - `https://lostfound.yourschool.org/auth/callback`
   - `http://localhost:5000/auth/callback` (for testing)
4. **Fill in `.env`.** Copy the client ID and secret into `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, set `ALLOWED_DOMAINS` and `STAFF_EMAILS`, and set `DEV_LOGIN=0`.
5. **Allow the app for students under 18.** Google Workspace for Education blocks under-18 users from third-party apps the admin hasn't configured. In the Google Admin console, go to **Security → Access and data control → API controls → App access control**, find this app's client ID, and mark it **Trusted**. Alternatively, turn on the setting that lets under-18 users use apps that request only basic sign-in info.

If students and staff are on different domains, list both, e.g. `ALLOWED_DOMAINS=district.org,students.district.org`. If the consent screen is Internal, both domains must belong to the same Workspace organization.

---

## Put it online for a school

Any host that runs Python and keeps files on disk works. The database (`data/lostfound.db`) and photos (`data/photos/`) live in `app/data/`, or wherever `DATA_DIR` points.

- **Render, Railway or Fly.io:** start command `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`, plus a persistent disk mounted at `DATA_DIR`.
- **A school or district server:** run the same gunicorn command behind nginx with HTTPS.

Checklist before going live:
- `DEV_LOGIN=0`
- A long random `SECRET_KEY`
- HTTPS on (Google sign-in requires it)
- `app/data/` backed up

**Cost:** hosting is usually under $10 a month. AI costs are in **What it costs** above.

---

## Who can use it

| Setting | Status |
|---|---|
| K–12 schools | **Ready.** Built for Google Workspace for Education. |
| Colleges | **Ready on Google Workspace.** Microsoft 365 campuses need Microsoft sign-in added. |
| Offices | **Small add.** Add Microsoft sign-in for Microsoft 365 companies, and rename "student" and "grade" in the page text. |
| Hospitals, hotels, venues | **Needs a guest mode.** Patients and visitors have no organization account, so they'd claim by phone or a desk code instead. A hospital also needs a privacy (HIPAA) review, because patient belongings can count as health information. |

---

## Privacy

- **Stored per student:** school email, the name and grade they type on a claim, and their claims.
- **Not visible to students:** where an item is stored, and other students' claims.
- **Photos:** re-encoded on upload, which removes location (GPS) data from phone photos. Only signed-in users can view them.
- **Sent to the Claude API:** item photos and descriptions, and the student's search text. Student names and emails are never sent.
- **Data agreements:** most districts need a data privacy agreement before student use. In New Jersey that's typically done through the NJ Student Data Privacy Consortium.

## Data shape

`items`: `tag` (LF-1234), `title`, `category`, `color`, `brand`, `description`, `keywords`, `photos`, `location` (staff only), `found_where`, `found_at`, `status` (`available` | `returned`), `returned_at`, `returned_to`, `logged_by`, `mock`

`claims`: `item_id`, `student_email`, `name`, `grade`, `proof`, `status` (`pending` | `approved` | `declined`), `note`, `created_at`, `decided_at`, `mock`
