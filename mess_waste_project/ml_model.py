"""Simple machine learning model: how much food should we cook?

MODEL   : Linear Regression 
PREDICTS: grams of a dish that ONE student will eat at a meal
ANSWER  : kg to cook = grams per student x students expected x 1.05

FACTORS (5):
  1. dish            (which dish it is)
  2. meal type       (breakfast, lunch or dinner)
  3. weekday         (Monday ... Sunday)
  4. last waste %    (how much of this dish was wasted the last time)
  5. last rating     (how students rated this dish the last time)

Run it:  python ml_model.py
"""
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from db import get_db
import crud

CATEGORY_FACTORS = ["dish_name", "meal_type", "day"]
NUMBER_FACTORS = ["last_waste_pct", "last_rating"]


# ---------------------------------------------------------------- step 1
def load_data():
    """Read meal logs, dishes and feedback from MongoDB (PyMongo)."""
    db = get_db()
    logs = pd.DataFrame(list(db.meal_logs.find()))
    dishes = pd.DataFrame(list(db.dishes.find({}, {"name": 1})))
    feedback = pd.DataFrame(list(db.feedback.find()))
    if logs.empty or dishes.empty:
        raise ValueError("No data found. Run setup_db.py first.")
    return logs, dishes, feedback


# ---------------------------------------------------------------- step 2
def build_table(logs, dishes, feedback):
    """Make one row per dish per meal, with the factors and the answer."""
    dishes = dishes.rename(columns={"_id": "dish_id", "name": "dish_name"})
    df = logs.merge(dishes, on="dish_id")

    # average rating each meal received (some meals have no feedback)
    if len(feedback):
        ratings = feedback.groupby("log_id")["rating"].mean()
        df["rating"] = df["_id"].map(ratings)
    else:
        df["rating"] = None
    df["rating"] = df["rating"].fillna(df["rating"].mean() if df["rating"].notna().any() else 3.0)

    df["date"] = pd.to_datetime(df["date"])
    df["day"] = df["date"].dt.day_name()
    df["waste_pct"] = df["wasted_kg"] / df["prepared_kg"] * 100

    # THE ANSWER we want to predict: grams eaten per student
    df["eaten_g"] = (df["prepared_kg"] - df["wasted_kg"]) * 1000 / df["students_served"]

    # History factors: look at the PREVIOUS meal of the same dish.
    # shift(1) moves values down one row, so a meal never sees its own result.
    df = df.sort_values(["dish_name", "date"])
    df["last_waste_pct"] = df.groupby("dish_name")["waste_pct"].shift(1)
    df["last_rating"] = df.groupby("dish_name")["rating"].shift(1)

    df = df.dropna(subset=["last_waste_pct"])        # first meal of a dish has no history
    return df.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------- step 3
def to_numbers(df, columns=None):
    """Turn words (dish, meal, weekday) into 0/1 columns the model can use."""
    X = pd.get_dummies(df[CATEGORY_FACTORS + NUMBER_FACTORS], columns=CATEGORY_FACTORS)
    if columns is not None:                         # match the columns used in training
        X = X.reindex(columns=columns, fill_value=0)
    return X.astype(float)


# ---------------------------------------------------------------- step 4
def train(df):
    """Train on the older meals, test on the newest 20% (meals it has not seen)."""
    cut = int(len(df) * 0.8)
    train_df, test_df = df.iloc[:cut], df.iloc[cut:]

    X_train = to_numbers(train_df)
    model = LinearRegression().fit(X_train, train_df["eaten_g"])

    predictions = model.predict(to_numbers(test_df, X_train.columns))
    model_error = mean_absolute_error(test_df["eaten_g"], predictions)

    # Compare with the plain average of each dish
    dish_avg = train_df.groupby("dish_name")["eaten_g"].mean()
    plain = test_df["dish_name"].map(dish_avg).fillna(train_df["eaten_g"].mean())
    plain_error = mean_absolute_error(test_df["eaten_g"], plain)

    # Now learn from ALL meals for real use
    X_all = to_numbers(df)
    final_model = LinearRegression().fit(X_all, df["eaten_g"])
    return {"model": final_model, "columns": X_all.columns, "table": df,
            "model_error": round(model_error, 1), "plain_error": round(plain_error, 1)}


# ---------------------------------------------------------------- step 5
def recommend(state, dish_name, meal_type, day, students):
    """How many kg should we cook?"""
    history = state["table"][state["table"]["dish_name"] == dish_name]
    if history.empty:
        raise ValueError("No history for this dish yet. Record its first meal.")
    last = history.sort_values("date").iloc[-1]       # the most recent meal of this dish
    row = pd.DataFrame([{
        "dish_name": dish_name, "meal_type": meal_type, "day": day,
        "last_waste_pct": last["waste_pct"], "last_rating": last["rating"]}])
    grams = float(state["model"].predict(to_numbers(row, state["columns"]))[0])
    kg = grams * students / 1000 * 1.05                # +5% safety margin
    return {"grams": round(grams), "kg": round(kg, 1), "history_meals": len(history),
            "last_date": last["date"], "last_prepared_kg": last["prepared_kg"],
            "last_wasted_kg": last["wasted_kg"], "last_waste_pct": round(last["waste_pct"], 1),
            "last_students": int(last["students_served"]),
            "avg_waste_pct": round(history["waste_pct"].mean(), 1),
            "avg_rating": round(history["rating"].mean(), 1)}


# ------------------------------------------------- used by the website
_state = None


def get_state():
    """Train automatically. It trains again by itself when new meals or
    feedback have been added, so the website needs no 'train' button."""
    global _state
    db = get_db()
    counts = (db.meal_logs.count_documents({}), db.feedback.count_documents({}))
    if _state is None or _state["counts"] != counts:
        table = build_table(*load_data())
        if len(table) < 20:
            raise ValueError("Not enough meals recorded yet to make a recommendation.")
        _state = train(table)
        _state["counts"] = counts
    return _state


def plan(dish_id, date_text, meal_type, students_expected):
    """Check the form values and return the recommendation."""
    dish = crud.get_dish(dish_id)
    if dish is None:
        raise ValueError("Dish not found.")
    try:
        students = int(students_expected)
    except (TypeError, ValueError):
        raise ValueError("Students expected must be a whole number.")
    if students < 1:
        raise ValueError("Students expected must be at least 1.")
    day = pd.Timestamp(crud.parse_date(date_text)).day_name()
    result = recommend(get_state(), dish["name"], meal_type, day, students)
    result.update({"dish": dish["name"], "day": day, "students": students})
    result.update(extra_details(result, dish, students))
    result["insights"] = insights(get_state(), dish["name"], meal_type, pd.Timestamp(crud.parse_date(date_text)))
    return result


def insights(state, dish_name, meal_type, planned):
    """Extra guidance from the same meal history (simple group averages)."""
    table = state["table"]
    mine = table[table["dish_name"] == dish_name]

    def best_worst(column):
        """Lowest and highest average waste share, only for groups with 2+ meals."""
        g = mine.groupby(column)["waste_pct"].agg(["mean", "count"])
        g = g[g["count"] >= 2]
        if len(g) < 2:
            return None
        return {"best": (g["mean"].idxmin(), round(g["mean"].min(), 1)),
                "worst": (g["mean"].idxmax(), round(g["mean"].max(), 1))}

    # other dishes that work well for the same meal (low waste, good rating)
    same_meal = table[table["meal_type"] == meal_type]
    g = same_meal.groupby("dish_name").agg(waste=("waste_pct", "mean"),
                                           rating=("rating", "mean"), meals=("waste_pct", "count"))
    g = g[(g["meals"] >= 3) & (g.index != dish_name)].sort_values("waste").head(3)
    alternatives = [{"name": n, "waste": round(r["waste"], 1), "rating": round(r["rating"], 1)}
                    for n, r in g.iterrows()]

    # was it served very recently?
    dates = mine["date"].sort_values()
    gap_note = None
    if len(dates) >= 3:
        typical = float(dates.diff().dt.days.dropna().median())
        since = (planned - dates.iloc[-1]).days
        if 0 <= since < typical / 2:
            gap_note = (f"This dish was served {since} day(s) ago. It is usually served about "
                        f"every {round(typical)} days, so students may be tired of it.")
    return {"by_meal": best_worst("meal_type"), "by_day": best_worst("day"),
            "alternatives": alternatives, "meal_type": meal_type, "gap_note": gap_note}


def extra_details(result, dish, students):
    """More useful numbers around the recommendation (all simple arithmetic)."""
    cost = dish["cost_per_kg"]
    needed = result["grams"] * students / 1000                 # food students will eat
    last_rate_kg = result["last_prepared_kg"] / result["last_students"] * students
    difference = round(last_rate_kg - result["kg"], 1)         # + means cook less than last time
    tips = []
    if result["last_waste_pct"] > 20:
        tips.append("More than 20% was wasted last time. Cooking the recommended amount should reduce this.")
    elif result["last_waste_pct"] < 8:
        tips.append("Waste was low last time, so keep the quantity close to the recommendation.")
    if result["avg_rating"] < 3:
        tips.append(f"Students rate this dish low (average {result['avg_rating']} out of 5). Check the taste or portion size.")
    return {
        "min_kg": round(needed, 1),                            # exactly what students are expected to eat
        "max_kg": round(needed * 1.10, 1),                     # 10% extra, the most worth cooking
        "cost_to_cook": round(result["kg"] * cost),
        "cost_per_kg": cost,
        "last_rate_kg": round(last_rate_kg, 1),                # last time's cooking rate for today's students
        "difference_kg": abs(difference),
        "cook_less": difference >= 0,
        "money_effect": abs(round(difference * cost)),
        "tips": tips,
    }


if __name__ == "__main__":
    table = build_table(*load_data())
    state = train(table)
    print(f"Meals used: {len(table)}")
    print(f"Average error of the model     : {state['model_error']} g per student")
    print(f"Average error of a plain average: {state['plain_error']} g per student")
    r = recommend(state, "Rajma Chawal", "dinner", "Monday", 420)
    print(f"Rajma Chawal, Monday dinner, 420 students -> {r['grams']} g each, cook {r['kg']} kg")
