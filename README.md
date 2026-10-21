# Lost & Found Desk

A school lost-and-found app.

- **Office staff** take 2–3 photos of a found item and say where it's stored. AI reads the photos and writes the description.
- **Students** describe what they lost in plain English. AI matches the description against everything on the shelf, and the student claims the item.
- **Staff** review each claim against the photos and approve or decline it. Approving marks the item returned.

## How it runs

`index.html` is a single-page app built as a Claude Artifact. It uses the Claude artifact runtime (`window.claude.use(...)`) for:

| Capability | Used for |
|---|---|
| `db` | Items and claims (shared, with access rules) |
| `assets` | Item photos |
| `sample` | AI photo description and plain-English matching |
| `user` | Knowing who is staff (Editor) vs student (Contributor) |

Opened outside Claude (for example on GitHub Pages), the page loads but shows "Open this page in Claude". To run it as a standalone website, replace those calls with a backend: Firebase (Firestore + Storage + Auth) and an AI API for the description and matching.

### Database access rules

```json
[
  { "path": "items",          "read": "view",     "write": "admin" },
  { "path": "claims",         "read": "admin",    "write": "admin" },
  { "path": "claims/{self}",  "read": "interact", "write": "interact" }
]
```

Everyone can read items; only staff can add or change them. Each student reads and writes only their own claims; staff read all claims.

## Data shape

**items/{id}**: `tag` (LF-1234), `title`, `category`, `color`, `brand`, `description`, `keywords[]`, `photos[]` (asset ids), `location` (staff only), `foundWhere`, `foundAt`, `status` (`available` | `returned`), `returnedAt`, `returnedTo`

**claims/{studentId}**: `{ claims: { [itemId]: { itemTag, itemTitle, name, grade, proof, status, createdAt, decidedAt } } }`

## Test data

`seed/` holds the scripts that generated the 121 mock middle-school items:

- `build.py` writes the item list, dates, storage spots and statuses.
- `draw.py` draws the illustrated item photos.

Run `python3 seed/build.py && python3 seed/draw.py` (needs Pillow). Every mock record has `mock: true` so it can be removed in one pass.
