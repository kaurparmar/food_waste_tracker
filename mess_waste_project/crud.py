"""CRUD functions (Create, Read, Update, Delete) using PyMongo.

No Flask code lives here, so both app.py (website) and main.py (console)
can use the same functions. Errors raised here:
  ValueError                        bad input (wrong number, bad date, unknown id)
  pymongo.errors.WriteError         MongoDB validation rejected the document
  pymongo.errors.DuplicateKeyError  unique index on dishes.name violated
"""
import re
from datetime import datetime, timedelta
from bson import ObjectId
from bson.errors import InvalidId
from db import get_db


# ---------------------------------------------------------------- helpers
def to_object_id(value):
    """Convert text from a URL or form into an ObjectId."""
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        raise ValueError("Invalid id: " + str(value))


def parse_date(value):
    """Convert 'YYYY-MM-DD' text into a datetime (MongoDB date type)."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format.")


def _num(value, label):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(label + " must be a number.")


def _int(value, label):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(label + " must be a whole number.")


def _dish_names(ids):
    """Return {dish_id: name} for the given ids."""
    rows = get_db().dishes.find({"_id": {"$in": list(ids)}}, {"name": 1})
    return {r["_id"]: r["name"] for r in rows}


# ----------------------------------------------------------------- dishes
def add_dish(name, category, cost_per_kg, tags=None, calories=None, protein_g=None):
    """CREATE a dish. Returns the new _id."""
    doc = {"name": name.strip(), "category": category,
           "cost_per_kg": _num(cost_per_kg, "Cost per kg")}
    if tags:
        doc["tags"] = [t.strip() for t in tags if t.strip()]
    nutrition = {}
    if calories not in (None, ""):
        nutrition["calories"] = _num(calories, "Calories")
    if protein_g not in (None, ""):
        nutrition["protein_g"] = _num(protein_g, "Protein")
    if nutrition:
        doc["nutrition"] = nutrition          # embedded document
    return get_db().dishes.insert_one(doc).inserted_id


def get_all_dishes(category=None):
    """READ all dishes (optionally one category), sorted by name."""
    query = {"category": category} if category else {}
    return list(get_db().dishes.find(query).sort("name", 1))


def search_dishes(text, category=None):
    """READ dishes whose name contains the text (case-insensitive)."""
    query = {"name": {"$regex": re.escape(text), "$options": "i"}}
    if category:
        query["category"] = category
    return list(get_db().dishes.find(query).sort("name", 1))


def get_dish(dish_id):
    """READ one dish by id (None if not found)."""
    return get_db().dishes.find_one({"_id": to_object_id(dish_id)})


def update_dish_cost(dish_id, cost):
    """UPDATE the cost with $set. Returns modified_count."""
    result = get_db().dishes.update_one(
        {"_id": to_object_id(dish_id)},
        {"$set": {"cost_per_kg": _num(cost, "Cost per kg")}})
    return result.modified_count


def add_dish_tag(dish_id, tag):
    """UPDATE: add one tag to the tags array with $push."""
    result = get_db().dishes.update_one(
        {"_id": to_object_id(dish_id)}, {"$push": {"tags": tag.strip()}})
    return result.modified_count


def delete_dish(dish_id):
    """DELETE a dish. Refused if meal logs still reference it."""
    oid = to_object_id(dish_id)
    db = get_db()
    if db.meal_logs.count_documents({"dish_id": oid}) > 0:
        raise ValueError("This dish has meal logs. Delete those logs first.")
    return db.dishes.delete_one({"_id": oid}).deleted_count


# -------------------------------------------------------------- meal logs
def add_log(date, meal_type, dish_id, prepared_kg, wasted_kg,
            students_served, hostel_block):
    """CREATE a meal log. Returns the new _id."""
    oid = to_object_id(dish_id)
    if get_dish(oid) is None:
        raise ValueError("Dish not found.")
    doc = {
        "date": parse_date(date), "meal_type": meal_type, "dish_id": oid,
        "prepared_kg": _num(prepared_kg, "Prepared kg"),
        "wasted_kg": _num(wasted_kg, "Wasted kg"),
        "students_served": _int(students_served, "Students served"),
        "hostel_block": hostel_block,
    }
    return get_db().meal_logs.insert_one(doc).inserted_id


def search_logs(start=None, end=None, meal_type=None, block=None,
                dish_id=None, limit=200):
    """READ logs with optional filters, newest first. Adds dish_name and waste_percent."""
    query = {}
    date_q = {}
    if start:
        date_q["$gte"] = parse_date(start)
    if end:
        date_q["$lt"] = parse_date(end) + timedelta(days=1)   # end day included
    if date_q:
        query["date"] = date_q
    if meal_type:
        query["meal_type"] = meal_type
    if block:
        query["hostel_block"] = block
    if dish_id:
        query["dish_id"] = to_object_id(dish_id)
    logs = list(get_db().meal_logs.find(query).sort("date", -1).limit(limit))
    names = _dish_names({l["dish_id"] for l in logs})
    for l in logs:
        l["dish_name"] = names.get(l["dish_id"], "(deleted dish)")
        l["waste_percent"] = round(l["wasted_kg"] / l["prepared_kg"] * 100, 1)
    return logs


def get_log(log_id):
    """READ one log by id."""
    return get_db().meal_logs.find_one({"_id": to_object_id(log_id)})


def update_log(log_id, prepared_kg=None, wasted_kg=None, students_served=None):
    """UPDATE selected fields of a log with $set. Returns modified_count."""
    fields = {}
    if prepared_kg not in (None, ""):
        fields["prepared_kg"] = _num(prepared_kg, "Prepared kg")
    if wasted_kg not in (None, ""):
        fields["wasted_kg"] = _num(wasted_kg, "Wasted kg")
    if students_served not in (None, ""):
        fields["students_served"] = _int(students_served, "Students served")
    if not fields:
        raise ValueError("Nothing to update.")
    return get_db().meal_logs.update_one(
        {"_id": to_object_id(log_id)}, {"$set": fields}).modified_count


def delete_log(log_id):
    """DELETE a log and all feedback that points to it."""
    oid = to_object_id(log_id)
    db = get_db()
    db.feedback.delete_many({"log_id": oid})
    return db.meal_logs.delete_one({"_id": oid}).deleted_count


# --------------------------------------------------------------- feedback
def add_feedback(log_id, student_roll, rating, comment=""):
    """CREATE a rating for a meal log."""
    oid = to_object_id(log_id)
    if get_log(oid) is None:
        raise ValueError("Meal log not found.")
    doc = {"log_id": oid, "student_roll": student_roll.strip(),
           "rating": _int(rating, "Rating"), "comment": comment.strip(),
           "date": datetime.now()}
    return get_db().feedback.insert_one(doc).inserted_id


def get_feedback_for_log(log_id):
    """READ all ratings of one log."""
    return list(get_db().feedback.find({"log_id": to_object_id(log_id)}))


def get_recent_feedback(limit=15):
    """READ the latest ratings with the dish name and meal info added."""
    db = get_db()
    items = list(db.feedback.find().sort("date", -1).limit(limit))
    logs = {l["_id"]: l for l in db.meal_logs.find(
        {"_id": {"$in": [i["log_id"] for i in items]}})}
    names = _dish_names({l["dish_id"] for l in logs.values()})
    for i in items:
        log = logs.get(i["log_id"])
        i["dish_name"] = names.get(log["dish_id"], "?") if log else "(deleted log)"
        i["meal_type"] = log["meal_type"] if log else ""
        i["log_date"] = log["date"] if log else None
    return items


def list_log_choices(limit=60):
    """Latest logs as (id, label) pairs for the feedback drop-down."""
    logs = search_logs(limit=limit)
    return [{"id": str(l["_id"]),
             "label": f"{l['date']:%d-%m-%Y} {l['meal_type']} - {l['dish_name']} (Block {l['hostel_block']})"}
            for l in logs]


def update_feedback(feedback_id, rating, comment=""):
    """UPDATE a rating and comment."""
    return get_db().feedback.update_one(
        {"_id": to_object_id(feedback_id)},
        {"$set": {"rating": _int(rating, "Rating"), "comment": comment.strip()}}
    ).modified_count


def delete_feedback(feedback_id):
    """DELETE one rating."""
    return get_db().feedback.delete_one({"_id": to_object_id(feedback_id)}).deleted_count
