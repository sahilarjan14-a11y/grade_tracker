import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "grades.db")

# 2nd year 33%, 3rd year 67%
YEAR_WEIGHTS = {2: 0.33, 3: 0.67}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                credits INTEGER NOT NULL DEFAULT 15,
                target_grade REAL NOT NULL DEFAULT 70,
                year INTEGER NOT NULL DEFAULT 2
            );
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                weighting REAL NOT NULL,
                score REAL
            );
        """)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(modules)").fetchall()]
        if "year" not in cols:
            conn.execute("ALTER TABLE modules ADD COLUMN year INTEGER NOT NULL DEFAULT 2")


def get_all_modules():
    with get_db() as conn:
        return conn.execute("SELECT * FROM modules ORDER BY year, name").fetchall()


def get_modules_by_year(year):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM modules WHERE year = ? ORDER BY name", (year,)
        ).fetchall()


def get_module(module_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()


def get_assessments(module_id):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM assessments WHERE module_id = ? ORDER BY name",
            (module_id,)
        ).fetchall()


def calc_module_stats(module_id):
    """
    Returns dict with:
      earned      - raw marks banked out of 100 (score * weighting / 100 summed)
      performance - normalised score on submitted work only (for grade badge)
      scored_weight - how much of the module has been assessed so far
    e.g. 80% on a 20% component -> earned=16, performance=80, scored_weight=20
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT weighting, score FROM assessments WHERE module_id = ? AND score IS NOT NULL",
            (module_id,)
        ).fetchall()
    if not rows:
        return {"earned": None, "performance": None, "scored_weight": 0}

    scored_weight = sum(r["weighting"] for r in rows)
    earned = sum(r["score"] * r["weighting"] for r in rows) / 100
    # performance is what you'd get if the whole module were this good
    performance = sum(r["score"] * r["weighting"] for r in rows) / scored_weight if scored_weight else None

    return {"earned": earned, "performance": performance, "scored_weight": scored_weight}


def calc_year_stats(year):
    """
    Returns (earned, possible) for a year.
    earned   - credit-weighted raw earned marks out of 100
    possible - credit-weighted marks possible from modules that have any data
    """
    modules = get_modules_by_year(year)
    total_credits_scored = 0
    total_credits_all = 0
    weighted_earned = 0

    for m in modules:
        stats = calc_module_stats(m["id"])
        total_credits_all += m["credits"]
        if stats["earned"] is not None:
            weighted_earned += stats["earned"] * m["credits"]
            total_credits_scored += m["credits"]

    if total_credits_all == 0:
        return None, None

    earned = weighted_earned / total_credits_all if total_credits_scored > 0 else None
    # possible is proportional to how many modules have been touched
    possible = (total_credits_scored / total_credits_all) * 100 if total_credits_scored > 0 else None
    return earned, possible


def calc_degree_stats():
    """
    Returns (earned, possible) on a 0-100 degree scale.
    e.g. if only year 2 has data and year 2 avg is 60:
      earned   = 60 * 0.33 = 19.8
      possible = 100 * 0.33 = 33
    Both years with data: possible = 100
    """
    earned = 0
    possible = 0
    has_any = False

    for year, weight in YEAR_WEIGHTS.items():
        modules = get_modules_by_year(year)
        if not modules:
            continue
        y_earned, y_possible = calc_year_stats(year)
        if y_earned is not None:
            earned += y_earned * weight
            possible += weight * 100
            has_any = True

    if not has_any:
        return None, None
    return earned, possible


def grade_label(score):
    if score is None:
        return ("N/A", "grade-na")
    if score >= 70:
        return ("First", "grade-first")
    if score >= 60:
        return ("2:1", "grade-upper")
    if score >= 50:
        return ("2:2", "grade-lower")
    if score >= 40:
        return ("Third", "grade-third")
    return ("Fail", "grade-fail")