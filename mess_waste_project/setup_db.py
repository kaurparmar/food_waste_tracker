"""Creates collections WITH validation rules and fills them with sample data.
Run: python setup_db.py   (safe to re-run; it RESETS dishes, meal_logs,
feedback)

The sample data is SIMULATED with built-in patterns so the prediction model
has something real to learn: dishes differ in popularity, weekends differ from
weekdays, breakfast differs from lunch, and students rate a dish lower when
more of it is wasted. State this in the report."""
from pymongo import MongoClient
from datetime import datetime, timedelta
import random

# name, category, cost/kg, tags, calories, protein, grams eaten per student, usual waste share
DISHES = [
    ("Rajma Chawal", "veg", 90, ["north-indian", "protein"], 420, 14, 190, .07),
    ("Paneer Butter Masala", "veg", 220, ["north-indian", "rich"], 480, 18, 150, .09),
    ("Chole Bhature", "veg", 110, ["punjabi", "fried"], 520, 15, 200, .12),
    ("Dal Tadka", "veg", 80, ["staple", "protein"], 300, 12, 140, .06),
    ("Aloo Paratha", "veg", 70, ["breakfast", "punjabi"], 350, 8, 170, .18),
    ("Poha", "veg", 60, ["breakfast", "light"], 250, 6, 130, .11),
    ("Idli Sambar", "veg", 65, ["south-indian", "light"], 220, 7, 150, .08),
    ("Chicken Curry", "non-veg", 280, ["protein", "spicy"], 450, 30, 180, .07),
    ("Egg Bhurji", "non-veg", 150, ["breakfast", "protein"], 300, 20, 120, .16),
    ("Mix Veg", "veg", 75, ["staple", "healthy"], 200, 5, 110, .14),
    ("Kheer", "dessert", 130, ["sweet", "festival"], 380, 8, 100, .13),
    ("Gulab Jamun", "dessert", 160, ["sweet"], 350, 5, 80, .12),
]
MEAL_WASTE = {"breakfast": 1.15, "lunch": .9, "dinner": 1.0}
MEAL_APPETITE = {"breakfast": .9, "lunch": 1.1, "dinner": 1.0}
COMMENTS = {5: ["Loved it"], 4: ["Tasty"], 3: ["Average"],
            2: ["Too oily", "Cold food"], 1: ["Needs more salt", "Too oily"]}


def create_collections(db):
    """Drop and recreate all collections with validators and indexes."""
    for name in ["dishes", "meal_logs", "feedback"]:
        db.drop_collection(name)

    db.create_collection("dishes", validator={"$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "category", "cost_per_kg"],
        "properties": {
            "name": {"bsonType": "string", "minLength": 2},
            "category": {"enum": ["veg", "non-veg", "dessert", "beverage"]},
            "cost_per_kg": {"bsonType": "number", "minimum": 1},
            "tags": {"bsonType": "array", "items": {"bsonType": "string"}},
            "nutrition": {"bsonType": "object", "properties": {
                "calories": {"bsonType": "number", "minimum": 0},
                "protein_g": {"bsonType": "number", "minimum": 0}}}}}})
    db.dishes.create_index("name", unique=True)

    db.create_collection("meal_logs", validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["date", "meal_type", "dish_id", "prepared_kg",
                         "wasted_kg", "students_served", "hostel_block"],
            "properties": {
                "date": {"bsonType": "date"},
                "meal_type": {"enum": ["breakfast", "lunch", "dinner"]},
                "dish_id": {"bsonType": "objectId"},
                "prepared_kg": {"bsonType": "number", "minimum": 1},
                "wasted_kg": {"bsonType": "number", "minimum": 0},
                "students_served": {"bsonType": "int", "minimum": 1},
                "hostel_block": {"enum": ["A", "B", "C"]}}},
        "$expr": {"$lte": ["$wasted_kg", "$prepared_kg"]}})   # waste never above cooked
    db.meal_logs.create_index("date")
    db.meal_logs.create_index("dish_id")

    db.create_collection("feedback", validator={"$jsonSchema": {
        "bsonType": "object",
        "required": ["log_id", "student_roll", "rating", "date"],
        "properties": {
            "log_id": {"bsonType": "objectId"},
            "student_roll": {"bsonType": "string"},
            "rating": {"bsonType": "int", "minimum": 1, "maximum": 5},
            "comment": {"bsonType": "string"},
            "date": {"bsonType": "date"}}}})



def make_dish_docs():
    return [{"name": n, "category": c, "cost_per_kg": cost, "tags": t,
             "nutrition": {"calories": cal, "protein_g": prot}}
            for n, c, cost, t, cal, prot, _, _ in DISHES]


def make_logs(dish_ids, today=None):
    """30 days x 3 meals x 2 dishes. Returns (log documents, waste share of each)."""
    today = today or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    logs, shares = [], []
    for d in range(30):
        day = today - timedelta(days=d)
        weekend = day.weekday() >= 5
        for meal in ["breakfast", "lunch", "dinner"]:
            for i in random.sample(range(len(dish_ids)), 2):
                appetite, base = DISHES[i][6], DISHES[i][7]
                students = random.randint(300, 500)
                eaten_kg = (students * appetite * MEAL_APPETITE[meal]
                            * (0.93 if weekend else 1) * random.uniform(.95, 1.05) / 1000)
                share = min(.35, base * MEAL_WASTE[meal] * (1.3 if weekend else 1)
                            * random.uniform(.85, 1.15))
                prepared = round(eaten_kg / (1 - share), 1)
                wasted = round(prepared * share, 1)
                logs.append({"date": day, "meal_type": meal, "dish_id": dish_ids[i],
                             "prepared_kg": prepared, "wasted_kg": wasted,
                             "students_served": students,
                             "hostel_block": random.choice(["A", "B", "C"])})
                shares.append(share)
    return logs, shares


def make_feedback(logs, shares, log_ids):
    """Students rate a dish lower when more of it was wasted."""
    fb = []
    for log, share, log_id in zip(logs, shares, log_ids):
        if random.random() > .85:
            continue
        for _ in range(random.choice([1, 2])):
            rating = int(min(5, max(1, round(4.6 - (share - .10) * 14 + random.uniform(-.8, .8)))))
            fb.append({"log_id": log_id, "student_roll": f"2210{random.randint(1000, 9999)}",
                       "rating": rating, "comment": random.choice(COMMENTS[rating]),
                       "date": log["date"]})
    return fb


def main():
    random.seed(7)   # same data every run
    db = MongoClient("mongodb://localhost:27017/")["mess_waste_db"]
    create_collections(db)
    dish_ids = db.dishes.insert_many(make_dish_docs()).inserted_ids
    print(f"Inserted {len(dish_ids)} dishes")
    logs, shares = make_logs(dish_ids)
    log_ids = db.meal_logs.insert_many(logs).inserted_ids
    print(f"Inserted {len(log_ids)} meal logs")
    fb = make_feedback(logs, shares, log_ids)
    db.feedback.insert_many(fb)
    print(f"Inserted {len(fb)} feedback entries")


if __name__ == "__main__":
    main()
