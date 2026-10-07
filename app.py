from flask import Flask, render_template, request, redirect
import db

app = Flask(__name__)
db.init_db()


def build_module_data(m):
    # build a fully-processed module dict including assessments
    avg = db.calc_module_average(m["id"])
    assessments = db.get_assessments(m["id"])
    label, css = db.grade_label(avg)
    target_label, target_css = db.grade_label(m["target_grade"])
    total_weight = sum(a["weighting"] for a in assessments)
    scored_weight = sum(a["weighting"] for a in assessments if a["score"] is not None)

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
        "average": avg,
        "label": label,
        "css": css,
        "total_weight": total_weight,
        "scored_weight": scored_weight,
        "assessments": assessments_data,
    }


# --- dashboard ---

@app.route("/")
def dashboard():
    year_data = {}
    for year in [2, 3]:
        modules = [build_module_data(m) for m in db.get_modules_by_year(year)]
        year_avg = db.calc_year_average(year)
        y_label, y_css = db.grade_label(year_avg)
        year_data[year] = {
            "modules": modules,
            "average": year_avg,
            "label": y_label,
            "css": y_css,
            "degree_weight": int(db.YEAR_WEIGHTS[year] * 100),
        }

    degree_avg = db.calc_degree_average()
    degree_label, degree_css = db.grade_label(degree_avg)
    total_modules = sum(len(year_data[y]["modules"]) for y in year_data)
    return render_template(
        "dashboard.html",
        year_data=year_data,
        degree_avg=degree_avg,
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


# --- assessment crud (all redirect back to dashboard) ---

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