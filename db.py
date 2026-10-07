import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "grades.db")

# 2nd year counts 33%, 3rd year counts 67% toward final degree
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
        # migrate existing dbs that predate the year column
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


def calc_module_average(module_id):
    # weighted mean of scored assessments only
    with get_db() as conn:
        rows = conn.execute(
            "SELECT weighting, score FROM assessments WHERE module_id = ? AND score IS NOT NULL",
            (module_id,)
        ).fetchall()
    if not rows:
        return None
    total_weight = sum(r["weighting"] for r in rows)
    if total_weight == 0:
        return None
    return sum(r["score"] * r["weighting"] for r in rows) / total_weight


def calc_year_average(year):
    # credit-weighted average across all modules in a given year
    modules = get_modules_by_year(year)
    total_credits = 0
    weighted_sum = 0
    for m in modules:
        avg = calc_module_average(m["id"])
        if avg is not None:
            weighted_sum += avg * m["credits"]
            total_credits += m["credits"]
    if total_credits == 0:
        return None
    return weighted_sum / total_credits


def calc_degree_average():
    # 2nd year: 33%, 3rd year: 67% - normalise over years that have data
    total_weight = 0
    weighted_sum = 0
    for year, weight in YEAR_WEIGHTS.items():
        avg = calc_year_average(year)
        if avg is not None:
            weighted_sum += avg * weight
            total_weight += weight
    if total_weight == 0:
        return None
    return weighted_sum / total_weight


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