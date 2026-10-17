"""Shows MongoDB validation rejecting bad data.
Run: python test_validation.py   (the website also uses run_tests())"""
from datetime import datetime
from pymongo.errors import WriteError, DuplicateKeyError
from db import get_db


def _attempt(case, action):
    try:
        action()
        return {"case": case, "outcome": "ACCEPTED", "detail": "Document was saved."}
    except DuplicateKeyError:
        return {"case": case, "outcome": "REJECTED",
                "detail": "Duplicate key: dish name must be unique."}
    except WriteError as e:
        return {"case": case, "outcome": "REJECTED",
                "detail": (e.details or {}).get("errmsg", "Document failed validation")}


def run_tests():
    db = get_db()
    dish = db.dishes.find_one()
    log = db.meal_logs.find_one()
    if dish is None or log is None:
        return [{"case": "Setup", "outcome": "REJECTED",
                 "detail": "No data found. Run python setup_db.py first."}]
    db.dishes.delete_many({"name": "Validation Test Dish"})
    results = [
        _attempt('Dish with category "snack" and cost -5',
                 lambda: db.dishes.insert_one({"name": "Bad Dish", "category": "snack", "cost_per_kg": -5})),
        _attempt("Meal log with wasted 25 kg but prepared 10 kg",
                 lambda: db.meal_logs.insert_one({
                     "date": datetime.now(), "meal_type": "lunch", "dish_id": dish["_id"],
                     "prepared_kg": 10.0, "wasted_kg": 25.0,
                     "students_served": 400, "hostel_block": "A"})),
        _attempt("Dish with a name that already exists",
                 lambda: db.dishes.insert_one({"name": dish["name"], "category": "veg", "cost_per_kg": 10})),
        _attempt("Feedback with rating 6",
                 lambda: db.feedback.insert_one({
                     "log_id": log["_id"], "student_roll": "221000000",
                     "rating": 6, "date": datetime.now()})),
        _attempt('Valid dish "Validation Test Dish"',
                 lambda: db.dishes.insert_one({"name": "Validation Test Dish",
                                               "category": "veg", "cost_per_kg": 50})),
    ]
    db.dishes.delete_many({"name": "Validation Test Dish"})   # clean up
    return results


if __name__ == "__main__":
    for r in run_tests():
        print(f"[{r['outcome']}] {r['case']}\n    {r['detail']}")
