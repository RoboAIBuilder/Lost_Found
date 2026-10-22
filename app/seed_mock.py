"""Load 121 mock middle-school items (35 with photos) and 4 pending claims for demos.

  python seed_mock.py          add the demo data (replaces any earlier demo data)
  python seed_mock.py --clear  remove only the demo data; items staff logged stay

Uses the same database and photo storage as the app (.env decides: local files, or Postgres + Vercel Blob).
In test mode on a deployed site, the staff Inventory tab has a "Reset demo data" button that does the same.
"""
import sys

import app as lf
import demo

def main():
    conn = lf.connect()
    try:
        if "--clear" in sys.argv:
            demo.clear(conn, lf.remove_photo)
            print("Demo data removed.")
        else:
            n_items, n_claims = demo.load(conn, lf.store_photo, lf.remove_photo)
            print(f"Loaded {n_items} demo items and {n_claims} claims.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
