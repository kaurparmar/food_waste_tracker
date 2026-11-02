"""Flask website for the Hostel Mess Food Waste Tracker.
Run: python app.py   then open http://127.0.0.1:5000
All database work is done by crud.py and analytics.py (PyMongo)."""
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo.errors import WriteError, DuplicateKeyError, PyMongoError
import ml_model
import crud
import analytics
import test_validation

app = Flask(__name__)
app.secret_key = "mess-waste-dev-key"   # needed for flash messages

CATEGORIES = ["veg", "non-veg", "dessert", "beverage"]
MEALS = ["breakfast", "lunch", "dinner"]
BLOCKS = ["A", "B", "C"]


@app.context_processor
def inject_lists():
    return {"CATEGORIES": CATEGORIES, "MEALS": MEALS, "BLOCKS": BLOCKS}


def friendly(exc):
    """Turn a database or input error into a short message for the user."""
    if isinstance(exc, DuplicateKeyError):
        return "That name already exists. Dish names must be unique."
    if isinstance(exc, WriteError):
        return "Rejected by MongoDB validation: " + str((exc.details or {}).get("errmsg", "invalid data"))
    if isinstance(exc, ValueError):
        return str(exc)
    return "Database error: " + str(exc)


# ------------------------------------------------------------------ home
@app.route("/")
def home():
    return render_template("home.html", stats=analytics.summary_stats(),
                           alerts=analytics.high_waste_logs(),
                           top=analytics.waste_per_dish(3))


# ---------------------------------------------------------------- dishes
@app.route("/dishes")
def dishes():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    if q:
        items = crud.search_dishes(q, category or None)
    else:
        items = crud.get_all_dishes(category or None)
    return render_template("dishes.html", dishes=items, q=q, category=category)


@app.route("/dishes/add", methods=["GET", "POST"])
def dish_add():
    form = request.form
    if request.method == "POST":
        try:
            tags = [t for t in form.get("tags", "").split(",")]
            crud.add_dish(form["name"], form["category"], form["cost_per_kg"],
                          tags, form.get("calories"), form.get("protein_g"))
            flash("Dish added.", "success")
            return redirect(url_for("dishes"))
        except (ValueError, PyMongoError) as e:
            flash(friendly(e), "error")
    return render_template("dish_form.html", mode="add", dish=None, form=form)


@app.route("/dishes/<dish_id>/edit", methods=["GET", "POST"])
def dish_edit(dish_id):
    dish = crud.get_dish(dish_id)
    if dish is None:
        return render_template("404.html"), 404
    if request.method == "POST":
        try:
            crud.update_dish_cost(dish_id, request.form["cost_per_kg"])
            tag = request.form.get("new_tag", "").strip()
            if tag:
                crud.add_dish_tag(dish_id, tag)
            flash("Dish updated.", "success")
            return redirect(url_for("dishes"))
        except (ValueError, PyMongoError) as e:
            flash(friendly(e), "error")
    return render_template("dish_form.html", mode="edit", dish=dish, form={})


@app.route("/dishes/<dish_id>/delete", methods=["POST"])
def dish_delete(dish_id):
    try:
        crud.delete_dish(dish_id)
        flash("Dish deleted.", "success")
    except (ValueError, PyMongoError) as e:
        flash(friendly(e), "error")
    return redirect(url_for("dishes"))


# ------------------------------------------------------------------ logs
@app.route("/logs")
def logs():
    f = {k: request.args.get(k, "") for k in ("start", "end", "meal_type", "block", "dish_id")}
    items = []
    try:
        items = crud.search_logs(f["start"], f["end"], f["meal_type"],
                                 f["block"], f["dish_id"])
    except ValueError as e:
        flash(friendly(e), "error")
    return render_template("logs.html", logs=items, f=f, dishes=crud.get_all_dishes())


@app.route("/logs/new", methods=["GET", "POST"])
def log_new():
    form = request.form
    if request.method == "POST":
        try:
            crud.add_log(form["date"], form["meal_type"], form["dish_id"],
                         form["prepared_kg"], form["wasted_kg"],
                         form["students_served"], form["hostel_block"])
            flash("Meal log saved.", "success")
            return redirect(url_for("logs"))
        except (ValueError, PyMongoError) as e:
            flash(friendly(e), "error")
    return render_template("log_form.html", dishes=crud.get_all_dishes(),
                           form=form, today=date.today().isoformat())


@app.route("/logs/<log_id>/delete", methods=["POST"])
def log_delete(log_id):
    try:
        crud.delete_log(log_id)
        flash("Log and its feedback deleted.", "success")
    except (ValueError, PyMongoError) as e:
        flash(friendly(e), "error")
    return redirect(url_for("logs"))


# -------------------------------------------------------------- feedback
@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        try:
            crud.add_feedback(request.form["log_id"], request.form["student_roll"],
                              request.form["rating"], request.form.get("comment", ""))
            flash("Thank you, feedback saved.", "success")
            return redirect(url_for("feedback"))
        except (ValueError, PyMongoError) as e:
            flash(friendly(e), "error")
    return render_template("feedback.html", choices=crud.list_log_choices(),
                           recent=crud.get_recent_feedback())


@app.route("/feedback/<feedback_id>/delete", methods=["POST"])
def feedback_delete(feedback_id):
    try:
        crud.delete_feedback(feedback_id)
        flash("Feedback deleted.", "success")
    except (ValueError, PyMongoError) as e:
        flash(friendly(e), "error")
    return redirect(url_for("feedback"))


# --------------------------------------------------------------- reports
REPORTS = {
    "waste_per_dish": lambda: analytics.waste_per_dish(8),
    "waste_by_meal": analytics.waste_percent_by_meal,
    "money_lost": analytics.money_lost_per_week,
    "ratings": analytics.dish_ratings,
    "waste_by_block": analytics.waste_by_block,
}


@app.route("/reports")
def reports():
    data = {name: fn() for name, fn in REPORTS.items()}
    return render_template("reports.html", data=data)


@app.route("/api/reports/<name>")
def report_json(name):
    if name not in REPORTS:
        return jsonify({"error": "unknown report"}), 404
    return jsonify(REPORTS[name]())          # JSON response for the charts


@app.route("/recommend")
def recommend():
    dish_id = request.args.get("dish_id", "")
    rows = []
    try:
        rows = analytics.cooking_recommendation(dish_id or None)
    except ValueError as e:
        flash(friendly(e), "error")
    return render_template("recommend.html", rows=rows, dish_id=dish_id,
                           dishes=crud.get_all_dishes())


@app.route("/validation-demo")
def validation_demo():
    return render_template("validation.html", results=test_validation.run_tests())


# ------------------------------------------------------ cooking planner
@app.route("/predict", methods=["GET", "POST"])
def predict():
    result = None
    if request.method == "POST":
        try:
            f = request.form
            result = ml_model.plan(f["dish_id"], f["date"], f["meal_type"],
                                   f["students_expected"])
        except (ValueError, PyMongoError) as e:
            flash(friendly(e), "error")
    return render_template("predict.html", result=result, form=request.form,
                           dishes=crud.get_all_dishes(),
                           today=date.today().isoformat())

# ---------------------------------------------------------- error pages
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(PyMongoError)
def db_error(e):
    return render_template("500.html", message=friendly(e)), 500


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html", message="Something went wrong on the server."), 500


if __name__ == "__main__":
    app.run(debug=True)
