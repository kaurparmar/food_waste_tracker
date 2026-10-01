from pymongo import MongoClient
from datetime import datetime, timedelta
import random

random.seed(7)  # same data every run

client = MongoClient("mongodb://localhost:27017/")
db = client["mess_waste_db"]

# Reset so the script can be re-run
for name in ["dishes", "meal_logs", "feedback"]:
    db.drop_collection(name)

# ---------- VALIDATION RULES ----------
db.create_collection("dishes", validator={"$jsonSchema": {
    "bsonType": "object",
    "required": ["name", "category", "cost_per_kg"],
    "properties": {
        "name": {"bsonType": "string", "minLength": 2},
        "category": {"enum": ["veg", "non-veg", "dessert", "beverage"]},
        "cost_per_kg": {"bsonType": "number", "minimum": 1},
        "tags": {"bsonType": "array", "items": {"bsonType": "string"}},
        "nutrition": {
            "bsonType": "object",
            "properties": {
                "calories": {"bsonType": "number", "minimum": 0},
                "protein_g": {"bsonType": "number", "minimum": 0}
            }
        }
    }
}})
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
            "hostel_block": {"enum": ["A", "B", "C"]}
        }
    },
    # Cross-field rule: waste can never exceed what was cooked
    "$expr": {"$lte": ["$wasted_kg", "$prepared_kg"]}
})

db.create_collection("feedback", validator={"$jsonSchema": {
    "bsonType": "object",
    "required": ["log_id", "student_roll", "rating", "date"],
    "properties": {
        "log_id": {"bsonType": "objectId"},
        "student_roll": {"bsonType": "string"},
        "rating": {"bsonType": "int", "minimum": 1, "maximum": 5},
        "comment": {"bsonType": "string"},
        "date": {"bsonType": "date"}
    }
}})

# ---------- SEED DATA ----------
dishes = [
    ("Rajma Chawal", "veg", 90, ["north-indian", "protein"], 420, 14),
    ("Paneer Butter Masala", "veg", 220, ["north-indian", "rich"], 480, 18),
    ("Chole Bhature", "veg", 110, ["punjabi", "fried"], 520, 15),
    ("Dal Tadka", "veg", 80, ["staple", "protein"], 300, 12),
    ("Aloo Paratha", "veg", 70, ["breakfast", "punjabi"], 350, 8),
    ("Poha", "veg", 60, ["breakfast", "light"], 250, 6),
    ("Idli Sambar", "veg", 65, ["south-indian", "light"], 220, 7),
    ("Chicken Curry", "non-veg", 280, ["protein", "spicy"], 450, 30),
    ("Egg Bhurji", "non-veg", 150, ["breakfast", "protein"], 300, 20),
    ("Mix Veg", "veg", 75, ["staple", "healthy"], 200, 5),
    ("Kheer", "dessert", 130, ["sweet", "festival"], 380, 8),
    ("Gulab Jamun", "dessert", 160, ["sweet"], 350, 5),
]
dish_docs = [{
    "name": n, "category": c, "cost_per_kg": cost, "tags": t,
    "nutrition": {"calories": cal, "protein_g": prot}
} for n, c, cost, t, cal, prot in dishes]

dish_ids = db.dishes.insert_many(dish_docs).inserted_ids
print(f"Inserted {len(dish_ids)} dishes")

# 30 days x 3 meals x 2 dishes = 180 meal logs
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
logs = []
for d in range(30):
    day = today - timedelta(days=d)
    for meal in ["breakfast", "lunch", "dinner"]:
        for dish_id in random.sample(dish_ids, 2):
            prepared = round(random.uniform(20, 60), 1)
            wasted = round(prepared * random.uniform(0.03, 0.25), 1)
            logs.append({
                "date": day,
                "meal_type": meal,
                "dish_id": dish_id,
                "prepared_kg": prepared,
                "wasted_kg": wasted,
                "students_served": random.randint(300, 500),
                "hostel_block": random.choice(["A", "B", "C"])
            })
log_ids = db.meal_logs.insert_many(logs).inserted_ids
print(f"Inserted {len(log_ids)} meal logs")

# 150 feedback entries
comments = ["Tasty", "Too oily", "Cold food", "Loved it", "Average", "Needs more salt"]
fb = [{
    "log_id": random.choice(log_ids),
    "student_roll": f"2210{random.randint(1000, 9999)}",
    "rating": random.randint(1, 5),
    "comment": random.choice(comments),
    "date": today - timedelta(days=random.randint(0, 29))
} for _ in range(150)]
db.feedback.insert_many(fb)
print(f"Inserted {len(fb)} feedback entries")