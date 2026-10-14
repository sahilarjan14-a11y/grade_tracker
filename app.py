from flask import Flask, render_template, request, redirect
import db

app = Flask(__name__)
db.init_db()


def build_module_data(m):
    stats = db.calc_module_stats(m["id"])
    assessments = db.get_assessments(m["id"])

    # earned = raw banked marks out of 100
    # performance = normalised score on submitted work (used for grade badge)
    earned = stats["earned"]
    performance = stats["performance"]
    scored_weight = stats["scored_weight"]
    total_weight = sum(a["weighting"] for a in assessments)

    # grade badge uses performance (how well they're doing on submitted work)
    label, css = db.grade_label(performance)
    target_label, target_css = db.grade_label(m["target_grade"])

    assessments_data = []
    for a in assessments:
        a_label, a_css = db.grade_label(a["score"])
        assessments_data.append({
            "id": a["id"],
            "name": a["name"],
            "weighting": a["weighting"],
            "score": a["score"],
            "label": a_label,
            "css": a_css,
            "contribution": round(a["score"] * a["weighting"] / 100, 2) if a["score"] is not None else None,
        })

    return {
        "id": m["id"],
        "name": m["name"],
        "credits": m["credits"],
        "year": m["year"],
        "target_grade": m["target_grade"],
        "target_label": target_label,
        "target_css": target_css,
        "earned": earned,           # raw marks banked (e.g. 16.00)
        "performance": performance,  # normalised performance (e.g. 80.00)
        "label": label,
        "css": css,
        "total_weight": total_weight,
        "scored_weight": scored_weight,
        "assessments": assessments_data,
    }


@app.route("/")
def dashboard():
    year_data = {}
    for year in [2, 3]:
        modules = [build_module_data(m) for m in db.get_modules_by_year(year)]
        y_earned, y_possible = db.calc_year_stats(year)
        # grade badge on year uses normalised performance (earned/possible*100)
        y_norm = (y_earned / y_possible * 100) if (y_earned is not None and y_possible) else None
        y_label, y_css = db.grade_label(y_norm)
        year_data[year] = {
            "modules": modules,
            "earned": y_earned,
            "possible": y_possible,
            "label": y_label,
            "css": y_css,
            "degree_weight": int(db.YEAR_WEIGHTS[year] * 100),
        }

    degree_earned, degree_possible = db.calc_degree_stats()
    # normalise for grade boundary classification
    degree_norm = (degree_earned / degree_possible * 100) if (degree_earned is not None and degree_possible) else None
    degree_label, degree_css = db.grade_label(degree_norm)
    total_modules = sum(len(year_data[y]["modules"]) for y in year_data)

    return render_template(
        "dashboard.html",
        year_data=year_data,
        degree_earned=degree_earned,
        degree_possible=degree_possible,
        degree_label=degree_label,
        degree_css=degree_css,
        total_modules=total_modules,
    )


# --- module crud ---

@app.route("/module/add", methods=["POST"])
def add_module():
    name = request.form["name"].strip()
    credits = int(request.form["credits"])
    target = float(request.form["target_grade"])
    year = int(request.form["year"])
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO modules (name, credits, target_grade, year) VALUES (?, ?, ?, ?)",
            (name, credits, target, year)
        )
    return redirect(f"/?tab={year}")


@app.route("/module/<int:module_id>/edit", methods=["GET", "POST"])
def edit_module(module_id):
    m = db.get_module(module_id)
    if request.method == "POST":
        name = request.form["name"].strip()
        credits = int(request.form["credits"])
        target = float(request.form["target_grade"])
        year = int(request.form["year"])
        with db.get_db() as conn:
            conn.execute(
                "UPDATE modules SET name=?, credits=?, target_grade=?, year=? WHERE id=?",
                (name, credits, target, year, module_id)
            )
        return redirect(f"/?tab={year}#module-{module_id}")
    return render_template("edit_module.html", module=m)


@app.route("/module/<int:module_id>/delete", methods=["POST"])
def delete_module(module_id):
    m = db.get_module(module_id)
    year = m["year"] if m else 2
    with db.get_db() as conn:
        conn.execute("DELETE FROM modules WHERE id=?", (module_id,))
    return redirect(f"/?tab={year}")


# --- assessment crud ---

@app.route("/module/<int:module_id>/assessment/add", methods=["POST"])
def add_assessment(module_id):
    m = db.get_module(module_id)
    name = request.form["name"].strip()
    weighting = float(request.form["weighting"])
    score_raw = request.form.get("score", "").strip()
    score = float(score_raw) if score_raw else None
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO assessments (module_id, name, weighting, score) VALUES (?, ?, ?, ?)",
            (module_id, name, weighting, score)
        )
    return redirect(f"/?tab={m['year']}#module-{module_id}")


@app.route("/assessment/<int:assessment_id>/edit", methods=["POST"])
def edit_assessment(assessment_id):
    name = request.form["name"].strip()
    weighting = float(request.form["weighting"])
    score_raw = request.form.get("score", "").strip()
    score = float(score_raw) if score_raw else None
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT a.module_id, m.year FROM assessments a JOIN modules m ON m.id=a.module_id WHERE a.id=?",
            (assessment_id,)
        ).fetchone()
        conn.execute(
            "UPDATE assessments SET name=?, weighting=?, score=? WHERE id=?",
            (name, weighting, score, assessment_id)
        )
    return redirect(f"/?tab={row['year']}#module-{row['module_id']}")


@app.route("/assessment/<int:assessment_id>/delete", methods=["POST"])
def delete_assessment(assessment_id):
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT a.module_id, m.year FROM assessments a JOIN modules m ON m.id=a.module_id WHERE a.id=?",
            (assessment_id,)
        ).fetchone()
        conn.execute("DELETE FROM assessments WHERE id=?", (assessment_id,))
    return redirect(f"/?tab={row['year']}#module-{row['module_id']}")


if __name__ == "__main__":
    app.run(debug=True)