"""Console menu for the Mess Waste Tracker (same crud.py and analytics.py as the website).
Run: python main.py"""
from datetime import date
from pymongo.errors import PyMongoError
import crud
import analytics
import test_validation

CATEGORIES = ["veg", "non-veg", "dessert", "beverage"]
MEALS = ["breakfast", "lunch", "dinner"]
BLOCKS = ["A", "B", "C"]


def ask(prompt):
    return input(prompt).strip()


def ask_choice(prompt, options):
    value = ask(f"{prompt} {options}: ").lower()
    if value not in [o.lower() for o in options]:
        raise ValueError("Choose one of " + ", ".join(options))
    return value if value in options else value.upper()


def print_table(rows, cols):
    """cols = [(header, key), ...]"""
    if not rows:
        print("  (no data)")
        return
    widths = [max(len(h), *(len(str(r.get(k, ""))) for r in rows)) for h, k in cols]
    line = "  ".join(h.ljust(w) for (h, _), w in zip(cols, widths))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(r.get(k, "")).ljust(w) for (_, k), w in zip(cols, widths)))


def pick_number(prompt, count):
    n = int(ask(prompt))
    if not 1 <= n <= count:
        raise ValueError("Number out of range.")
    return n - 1


def pick_dish():
    dishes = crud.get_all_dishes()
    for i, d in enumerate(dishes, 1):
        print(f"{i:>2}. {d['name']} ({d['category']}, Rs {d['cost_per_kg']}/kg)")
    return dishes[pick_number("Choose dish number: ", len(dishes))]


def pick_log():
    logs = crud.search_logs(limit=15)
    for i, l in enumerate(logs, 1):
        print(f"{i:>2}. {l['date']:%d-%m-%Y} {l['meal_type']:<9} {l['dish_name']} "
              f"(Block {l['hostel_block']}, wasted {l['wasted_kg']} kg)")
    return logs[pick_number("Choose log number: ", len(logs))]


def add_dish():
    name = ask("Dish name: ")
    category = ask_choice("Category", CATEGORIES)
    cost = ask("Cost per kg (Rs): ")
    tags = ask("Tags (comma separated, optional): ").split(",")
    crud.add_dish(name, category, cost, tags, ask("Calories (optional): "), ask("Protein g (optional): "))
    print("Dish added.")


def view_dishes():
    text = ask("Search name (Enter for all): ")
    dishes = crud.search_dishes(text) if text else crud.get_all_dishes()
    rows = [{"name": d["name"], "category": d["category"], "cost": d["cost_per_kg"],
             "tags": ", ".join(d.get("tags", []))} for d in dishes]
    print_table(rows, [("Name", "name"), ("Category", "category"), ("Rs/kg", "cost"), ("Tags", "tags")])


def update_cost():
    dish = pick_dish()
    count = crud.update_dish_cost(dish["_id"], ask("New cost per kg: "))
    print("Updated." if count else "No change.")


def delete_dish():
    dish = pick_dish()
    print("Deleted." if crud.delete_dish(dish["_id"]) else "Nothing deleted.")


def log_waste():
    dish = pick_dish()
    d = ask(f"Date YYYY-MM-DD (Enter for {date.today()}): ") or date.today().isoformat()
    crud.add_log(d, ask_choice("Meal", MEALS), dish["_id"], ask("Prepared kg: "),
                 ask("Wasted kg: "), ask("Students served: "), ask_choice("Block", BLOCKS))
    print("Meal log saved.")


def search_logs():
    start = ask("From date YYYY-MM-DD (optional): ")
    end = ask("To date YYYY-MM-DD (optional): ")
    meal = ask("Meal type (optional): ").lower()
    block = ask("Block A/B/C (optional): ").upper()
    logs = crud.search_logs(start, end, meal or None, block or None)
    rows = [{"date": f"{l['date']:%d-%m-%Y}", "meal": l["meal_type"], "dish": l["dish_name"],
             "block": l["hostel_block"], "prep": l["prepared_kg"], "waste": l["wasted_kg"],
             "pct": l["waste_percent"]} for l in logs[:30]]
    print_table(rows, [("Date", "date"), ("Meal", "meal"), ("Dish", "dish"), ("Block", "block"),
                       ("Prepared", "prep"), ("Wasted", "waste"), ("Waste %", "pct")])
    print(f"{len(logs)} record(s) found (first 30 shown).")


def edit_log():
    log = pick_log()
    count = crud.update_log(log["_id"], wasted_kg=ask("New wasted kg: "))
    print("Updated." if count else "No change.")


def add_feedback():
    log = pick_log()
    crud.add_feedback(log["_id"], ask("Student roll no: "), ask("Rating 1-5: "), ask("Comment: "))
    print("Feedback saved.")


def reports():
    print("\n1 Waste per dish  2 Waste % by meal  3 Money lost per week\n"
          "4 Dish ratings  5 Waste by block  6 Cooking recommendation")
    choice = ask("Report: ")
    if choice == "1":
        print_table(analytics.waste_per_dish(5), [("Dish", "name"), ("Wasted kg", "total_wasted_kg"),
                    ("Waste %", "waste_percent"), ("Money lost Rs", "money_lost")])
    elif choice == "2":
        print_table(analytics.waste_percent_by_meal(), [("Meal", "meal_type"), ("Wasted kg", "wasted_kg"),
                    ("Prepared kg", "prepared_kg"), ("Waste %", "waste_percent")])
    elif choice == "3":
        print_table(analytics.money_lost_per_week(), [("Year", "year"), ("Week", "week"),
                    ("Wasted kg", "wasted_kg"), ("Money lost Rs", "money_lost")])
    elif choice == "4":
        print_table(analytics.dish_ratings(), [("Dish", "name"), ("Avg rating", "avg_rating"), ("Votes", "votes")])
    elif choice == "5":
        print_table(analytics.waste_by_block(), [("Block", "block"), ("Wasted kg", "wasted_kg"),
                    ("Waste %", "waste_percent"), ("g per student", "grams_per_student")])
    elif choice == "6":
        print_table(analytics.cooking_recommendation()[:30], [("Dish", "name"), ("Meal", "meal_type"),
                    ("Avg cooked", "avg_prepared"), ("Avg wasted", "avg_wasted"), ("Suggested kg", "suggested_kg")])
    else:
        print("Invalid report number.")


def validation_demo():
    for r in test_validation.run_tests():
        print(f"[{r['outcome']}] {r['case']}\n      {r['detail']}")


MENU = [
    ("Add dish", add_dish), ("View / search dishes", view_dishes),
    ("Update dish cost", update_cost), ("Delete dish", delete_dish),
    ("Log meal waste", log_waste), ("Search meal logs", search_logs),
    ("Add feedback", add_feedback), ("Reports (aggregations)", reports),
    ("Validation demo", validation_demo), ("Edit wasted kg of a log", edit_log),
]


def main():
    while True:
        print("\n===== HOSTEL MESS WASTE TRACKER =====")
        for i, (label, _) in enumerate(MENU, 1):
            print(f"{i:>2}. {label}")
        print(" 0. Exit")
        choice = ask("Enter choice: ")
        if choice == "0":
            print("Goodbye.")
            break
        try:
            if not choice.isdigit() or not 1 <= int(choice) <= len(MENU):
                raise ValueError("Please enter a number from the menu.")
            MENU[int(choice) - 1][1]()
        except ValueError as e:
            print("Input problem:", e)
        except PyMongoError as e:
            print("Database problem:", e)


if __name__ == "__main__":
    main()
