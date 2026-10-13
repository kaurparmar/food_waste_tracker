"""Aggregation pipelines. Each function builds a pipeline, runs aggregate()
and returns a list of plain dictionaries (no ObjectIds) so the results can be
shown in tables, charts and JSON."""
from datetime import datetime, timedelta
from db import get_db
from crud import to_object_id

_JOIN_DISH = [
    {"$lookup": {"from": "dishes", "localField": "dish_id",
                 "foreignField": "_id", "as": "dish"}},
    {"$unwind": "$dish"},
]


def waste_per_dish(limit=5):
    """A1: dishes ranked by total wasted kg."""
    pipeline = [
        {"$group": {"_id": "$dish_id",
                    "total_wasted": {"$sum": "$wasted_kg"},
                    "total_prepared": {"$sum": "$prepared_kg"}}},
        {"$lookup": {"from": "dishes", "localField": "_id",
                     "foreignField": "_id", "as": "dish"}},
        {"$unwind": "$dish"},
        {"$project": {
            "_id": 0, "name": "$dish.name", "category": "$dish.category",
            "total_wasted_kg": {"$round": ["$total_wasted", 1]},
            "waste_percent": {"$round": [{"$multiply": [
                {"$divide": ["$total_wasted", "$total_prepared"]}, 100]}, 1]},
            "money_lost": {"$round": [
                {"$multiply": ["$total_wasted", "$dish.cost_per_kg"]}, 0]}}},
        {"$sort": {"total_wasted_kg": -1}},
        {"$limit": limit},
    ]
    return list(get_db().meal_logs.aggregate(pipeline))


def waste_percent_by_meal():
    """A2: waste percentage for breakfast, lunch and dinner."""
    pipeline = [
        {"$group": {"_id": "$meal_type",
                    "wasted": {"$sum": "$wasted_kg"},
                    "prepared": {"$sum": "$prepared_kg"}}},
        {"$project": {
            "_id": 0, "meal_type": "$_id",
            "wasted_kg": {"$round": ["$wasted", 1]},
            "prepared_kg": {"$round": ["$prepared", 1]},
            "waste_percent": {"$round": [{"$multiply": [
                {"$divide": ["$wasted", "$prepared"]}, 100]}, 1]}}},
        {"$sort": {"waste_percent": -1}},
    ]
    return list(get_db().meal_logs.aggregate(pipeline))


def money_lost_per_week():
    """A3: rupees lost to waste in each ISO week."""
    pipeline = _JOIN_DISH + [
        {"$group": {
            "_id": {"year": {"$isoWeekYear": "$date"}, "week": {"$isoWeek": "$date"}},
            "money_lost": {"$sum": {"$multiply": ["$wasted_kg", "$dish.cost_per_kg"]}},
            "wasted_kg": {"$sum": "$wasted_kg"}}},
        {"$sort": {"_id.year": 1, "_id.week": 1}},
        {"$project": {"_id": 0, "year": "$_id.year", "week": "$_id.week",
                      "wasted_kg": {"$round": ["$wasted_kg", 1]},
                      "money_lost": {"$round": ["$money_lost", 0]}}},
    ]
    return list(get_db().meal_logs.aggregate(pipeline))


def dish_ratings():
    """A4: average rating per dish (feedback -> meal_logs -> dishes)."""
    pipeline = [
        {"$lookup": {"from": "meal_logs", "localField": "log_id",
                     "foreignField": "_id", "as": "log"}},
        {"$unwind": "$log"},
        {"$group": {"_id": "$log.dish_id", "avg_rating": {"$avg": "$rating"},
                    "votes": {"$sum": 1}}},
        {"$lookup": {"from": "dishes", "localField": "_id",
                     "foreignField": "_id", "as": "dish"}},
        {"$unwind": "$dish"},
        {"$project": {"_id": 0, "name": "$dish.name",
                      "avg_rating": {"$round": ["$avg_rating", 2]}, "votes": 1}},
        {"$sort": {"avg_rating": -1}},
    ]
    return list(get_db().feedback.aggregate(pipeline))


def waste_by_block(days=30):
    """A5: waste per hostel block in the last N days."""
    since = datetime.now() - timedelta(days=days)
    pipeline = [
        {"$match": {"date": {"$gte": since}}},
        {"$group": {"_id": "$hostel_block",
                    "wasted": {"$sum": "$wasted_kg"},
                    "prepared": {"$sum": "$prepared_kg"},
                    "students": {"$sum": "$students_served"}}},
        {"$project": {
            "_id": 0, "block": "$_id",
            "wasted_kg": {"$round": ["$wasted", 1]},
            "waste_percent": {"$round": [{"$multiply": [
                {"$divide": ["$wasted", "$prepared"]}, 100]}, 1]},
            "grams_per_student": {"$round": [{"$divide": [
                {"$multiply": ["$wasted", 1000]}, "$students"]}, 0]}}},
        {"$sort": {"wasted_kg": -1}},
    ]
    return list(get_db().meal_logs.aggregate(pipeline))


def cooking_recommendation(dish_id=None):
    """A6: suggested kg per dish and meal = average food actually eaten + 5%."""
    pipeline = []
    if dish_id:
        pipeline.append({"$match": {"dish_id": to_object_id(dish_id)}})
    pipeline += [
        {"$group": {
            "_id": {"dish": "$dish_id", "meal": "$meal_type"},
            "avg_prepared": {"$avg": "$prepared_kg"},
            "avg_wasted": {"$avg": "$wasted_kg"},
            "avg_eaten": {"$avg": {"$subtract": ["$prepared_kg", "$wasted_kg"]}},
            "times_served": {"$sum": 1}}},
        {"$lookup": {"from": "dishes", "localField": "_id.dish",
                     "foreignField": "_id", "as": "dish"}},
        {"$unwind": "$dish"},
        {"$project": {
            "_id": 0, "name": "$dish.name", "meal_type": "$_id.meal",
            "times_served": 1,
            "avg_prepared": {"$round": ["$avg_prepared", 1]},
            "avg_wasted": {"$round": ["$avg_wasted", 1]},
            "suggested_kg": {"$round": [{"$multiply": ["$avg_eaten", 1.05]}, 1]}}},
        {"$sort": {"name": 1, "meal_type": 1}},
    ]
    return list(get_db().meal_logs.aggregate(pipeline))


def summary_stats():
    """Totals for the home page."""
    db = get_db()
    rows = list(db.meal_logs.aggregate(_JOIN_DISH + [
        {"$group": {"_id": None, "logs": {"$sum": 1},
                    "prepared": {"$sum": "$prepared_kg"},
                    "wasted": {"$sum": "$wasted_kg"},
                    "money": {"$sum": {"$multiply": ["$wasted_kg", "$dish.cost_per_kg"]}}}}]))
    rate = list(db.feedback.aggregate([
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "votes": {"$sum": 1}}}]))
    s = rows[0] if rows else {"logs": 0, "prepared": 0, "wasted": 0, "money": 0}
    return {
        "dishes": db.dishes.count_documents({}),
        "logs": s["logs"],
        "wasted_kg": round(s["wasted"], 1),
        "waste_percent": round(s["wasted"] / s["prepared"] * 100, 1) if s["prepared"] else 0,
        "money_lost": round(s["money"]),
        "avg_rating": round(rate[0]["avg"], 2) if rate else 0,
        "votes": rate[0]["votes"] if rate else 0,
    }


def high_waste_logs(threshold=20, limit=8):
    """Needs attention: logs where more than `threshold` percent was wasted."""
    pipeline = [
        {"$match": {"$expr": {"$gt": [{"$multiply": [
            {"$divide": ["$wasted_kg", "$prepared_kg"]}, 100]}, threshold]}}},
    ] + _JOIN_DISH + [
        {"$project": {
            "_id": 0, "date": 1, "meal_type": 1, "hostel_block": 1,
            "name": "$dish.name", "prepared_kg": 1, "wasted_kg": 1,
            "waste_percent": {"$round": [{"$multiply": [
                {"$divide": ["$wasted_kg", "$prepared_kg"]}, 100]}, 1]}}},
        {"$sort": {"waste_percent": -1}},
        {"$limit": limit},
    ]
    return list(get_db().meal_logs.aggregate(pipeline))
