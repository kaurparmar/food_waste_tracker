# Hostel Mess Food Waste Tracker

**Course:** CSE494 Intelligent NoSQL Databases (Academic Task 2)
**Stack:** Python 3, MongoDB, PyMongo, Flask, HTML/CSS, Chart.js
**Author:** Arminderdeep

A website for a hostel mess that records how much cooked food is prepared and wasted for every dish and meal, validates the data inside MongoDB, and uses aggregation pipelines to answer questions such as: which dish wastes the most, how much money is lost per week, and how much should be cooked next time.

> All files listed below are included in this project folder.

---

## 1. Problem and goals

- Hostel messes cook in bulk and a share is thrown away daily, but nobody records which dish, meal or block is responsible.
- This project stores every serving as a document, rejects impossible values, and turns the records into decisions.
- **Course requirements covered:** document design, validation rules, CRUD, PyMongo integration, aggregation queries, explainable queries and output.

## 2. Features

| Module | What it does |
|---|---|
| Dish management | Add, view, search, edit cost, add tags, delete dishes |
| Meal waste logging | Record prepared and wasted kg per dish, meal and hostel block |
| Search and filter | Filter logs by date range, meal type, block and dish |
| Student feedback | Rate a meal 1 to 5 with a comment |
| Reports | Six aggregation reports with tables and charts |
| Cooking recommendation | Suggests how much to cook per dish and meal from past data |
| Validation demo | Shows MongoDB rejecting bad data |
| Error pages | Custom 404 and 500 pages |

---

## 3. Prerequisites

1. **Python 3.9 or newer** (`python --version`)
2. **MongoDB Community Server** (default port 27017) and **MongoDB Compass**
3. A code editor such as VS Code

## 4. Setup instructions (Windows)

```bash
# 1. Create the project folder
mkdir mess_waste_project
cd mess_waste_project

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install flask pymongo

# 4. Save the dependency list
pip freeze > requirements.txt

# 5. Create the database, validators and sample data
python setup_db.py

# 6. Run the website
python app.py
```

Open **http://127.0.0.1:5000** in the browser.

**Mac/Linux:** activate with `source venv/bin/activate`.
**Check MongoDB:** open Compass and connect to `mongodb://localhost:27017`. If it connects, MongoDB is running.

---

## 5. Project structure

```
mess_waste_project/
|-- app.py                  [done]  Flask app: routes and error handlers
|-- db.py                   [done]  PyMongo connection
|-- crud.py                 [done]  Create, read, update, delete functions
|-- analytics.py            [done]  Aggregation pipelines
|-- setup_db.py             [done]      Collections, validators, indexes, seed data
|-- test_validation.py      [done]      Demonstrates rejected writes
|-- requirements.txt        [done]  Dependency list
|-- README.md               this file
|-- templates/              HTML pages (Jinja2)
|   |-- base.html           Common layout and navigation
|   |-- home.html           Summary numbers and quick links
|   |-- dishes.html         Dish list, search, delete buttons
|   |-- dish_form.html      Add or edit dish
|   |-- logs.html           Search and filter meal logs
|   |-- log_form.html       Record meal waste
|   |-- feedback.html       Rating form and recent feedback
|   |-- reports.html        Report tabs, tables and charts
|   |-- recommend.html      Cooking recommendation page
|   |-- validation.html     Validation demo results
|   |-- 404.html            Page not found
|   `-- 500.html            Server error
`-- static/
    |-- css/style.css       Site styling
    `-- js/charts.js        Chart.js chart drawing
```

---

## 6. Database design

**Database:** `mess_waste_db`

### dishes
| Field | Type | Rule |
|---|---|---|
| `_id` | ObjectId | primary key |
| `name` | string | required, min length 2, **unique index** |
| `category` | string | required, one of veg, non-veg, dessert, beverage |
| `cost_per_kg` | number | required, minimum 1 |
| `tags` | array of strings | optional |
| `nutrition` | embedded object | `calories`, `protein_g`, each minimum 0 |

### meal_logs
| Field | Type | Rule |
|---|---|---|
| `_id` | ObjectId | primary key |
| `date` | date | required |
| `meal_type` | string | breakfast, lunch or dinner |
| `dish_id` | ObjectId | required, **reference** to dishes |
| `prepared_kg` | number | required, minimum 1 |
| `wasted_kg` | number | required, minimum 0, **never above prepared_kg** |
| `students_served` | int | required, minimum 1 |
| `hostel_block` | string | A, B or C |

### feedback
| Field | Type | Rule |
|---|---|---|
| `_id` | ObjectId | primary key |
| `log_id` | ObjectId | required, **reference** to meal_logs |
| `student_roll` | string | required |
| `rating` | int | required, 1 to 5 |
| `comment` | string | optional |
| `date` | date | required |

**Design decisions (viva answers)**
- `nutrition` is **embedded** because it is always read with the dish and never grows.
- `meal_logs` and `feedback` are **referenced** because they grow without limit and are queried on their own. `$lookup` joins them.
- Relationships: one dish has many logs; one log has many ratings.

**Validation mechanisms:** `$jsonSchema` (types, required, enum, min and max), `$expr` for the cross-field rule `wasted_kg <= prepared_kg`, and a unique index on `dishes.name`. Violations raise `pymongo.errors.WriteError` or `DuplicateKeyError`, which the website catches and shows as a friendly message.

---

## 7. File-by-file reference

### `db.py` [done]
Creates one shared MongoDB connection.

| Function | Purpose |
|---|---|
| `get_client()` | Returns a single `MongoClient("mongodb://localhost:27017/")` |
| `get_db()` | Returns the `mess_waste_db` database object |

### `setup_db.py` [done]
Run once, and again any time to reset. Drops the three collections, recreates them with validators, builds the unique index, then seeds 12 dishes, 180 meal logs (30 days x 3 meals x 2 dishes) and 150 feedback entries using `random.seed(7)` so data is repeatable.

### `test_validation.py` [done]
Tries a bad dish and an impossible waste value, and prints that MongoDB blocked them. Source of the validation screenshots.

### `crud.py` [done]
All Create, Read, Update, Delete operations. No Flask code here, only PyMongo.

**Helper**
| Function | Purpose |
|---|---|
| `to_object_id(text)` | Converts a string from a URL or form into an `ObjectId` |

**Dishes**
| Function | PyMongo call | Purpose |
|---|---|---|
| `add_dish(name, category, cost_per_kg, tags, calories, protein_g)` | `insert_one` | Create a dish |
| `get_all_dishes(category=None)` | `find` | List dishes, optional category filter |
| `search_dishes(text)` | `find` with `$regex` | Case-insensitive name search |
| `get_dish(dish_id)` | `find_one` | Fetch one dish |
| `update_dish_cost(dish_id, cost)` | `update_one` with `$set` | Change the cost per kg |
| `add_dish_tag(dish_id, tag)` | `update_one` with `$push` | Add a tag |
| `delete_dish(dish_id)` | `delete_one` | Remove a dish |

**Meal logs**
| Function | PyMongo call | Purpose |
|---|---|---|
| `add_log(date, meal_type, dish_id, prepared_kg, wasted_kg, students_served, hostel_block)` | `insert_one` | Record a serving |
| `search_logs(start=None, end=None, meal_type=None, block=None, dish_id=None)` | `find`, `$gte`, `$lte`, `.sort` | Filter logs, newest first |
| `get_log(log_id)` | `find_one` | Fetch one log |
| `update_log(log_id, fields)` | `update_one` with `$set` | Correct a log |
| `delete_log(log_id)` | `delete_one` plus `delete_many` on feedback | Remove a log and its ratings |

**Feedback**
| Function | PyMongo call | Purpose |
|---|---|---|
| `add_feedback(log_id, student_roll, rating, comment)` | `insert_one` | Save a rating |
| `get_feedback_for_log(log_id)` | `find` | Ratings for one meal |
| `update_feedback(feedback_id, rating, comment)` | `update_one` | Edit a rating |
| `delete_feedback(feedback_id)` | `delete_one` | Remove a rating |

### `analytics.py` [done]
Aggregation pipelines. Each function builds a pipeline, runs `aggregate()` and returns a list of dictionaries.

| Function | Question answered | Stages |
|---|---|---|
| `waste_per_dish(limit=5)` | Which dishes waste the most? | `$group`, `$lookup`, `$unwind`, `$sort`, `$limit` |
| `waste_percent_by_meal()` | Which meal type has the highest waste %? | `$group`, `$project` (`$divide`, `$multiply`), `$sort` |
| `money_lost_per_week()` | How much money is lost each week? | `$lookup`, `$unwind`, `$project` (`$isoWeek`), `$group`, `$sort` |
| `dish_ratings()` | Which dishes are rated best and worst? | `$lookup` (twice), `$unwind`, `$group` with `$avg`, `$sort` |
| `waste_by_block(days=30)` | Which hostel block wastes the most? | `$match`, `$group`, `$project`, `$sort` |
| `cooking_recommendation(dish_id=None)` | How much should be cooked next time? | `$group` by dish and meal type, `$project`, `$sort` |
| `summary_stats()` | Totals for the home page | `$group` over all logs |

**Recommendation rule:** for each dish and meal type, average the food actually eaten (`prepared_kg - wasted_kg`) and add a 5% safety margin. That is the suggested kilograms.

### `app.py` [done]
The Flask website. Imports `crud` and `analytics`, defines routes, shows success or error messages with Flask `flash`, and registers custom error pages.

| Route | Method | Page / action |
|---|---|---|
| `/` | GET | Home summary |
| `/dishes` | GET | List dishes; `?q=` searches by name |
| `/dishes/add` | GET, POST | Add dish form |
| `/dishes/<dish_id>/edit` | GET, POST | Edit cost and tags |
| `/dishes/<dish_id>/delete` | POST | Delete a dish |
| `/logs` | GET | Search and filter logs |
| `/logs/new` | GET, POST | Record meal waste |
| `/logs/<log_id>/delete` | POST | Delete a log |
| `/feedback` | GET, POST | Submit and view ratings |
| `/reports` | GET | Report tabs and charts |
| `/recommend` | GET | Cooking recommendation table |
| `/validation-demo` | GET | Runs bad inserts and shows rejections |
| `/api/reports/<name>` | GET | JSON data for the charts |

Error handlers: `404` renders `404.html`, `500` renders `500.html`. Every database write is wrapped in `try/except` for `WriteError`, `DuplicateKeyError` and invalid ObjectIds.

### `templates/`
Jinja2 pages that all extend `base.html` (navigation bar, flash messages, footer). Data arrives from `app.py`; no database code lives in templates.

### `static/`
`css/style.css` holds the layout, colours and a media query for small screens. `js/charts.js` draws bar charts using Chart.js loaded from a CDN.

---

## 8. Suggested build order

1. `db.py` then test the connection with `get_db().list_collection_names()`.
2. `crud.py` one function at a time; test each in a small script or the Python shell.
3. `analytics.py` one pipeline at a time; first run each in Compass's Aggregations tab, then copy to Python.
4. `app.py` with `base.html`, then dishes, logs, feedback, reports, recommendation.
5. Error pages, validation demo page, styling.
6. Real screenshots, report and viva practice.

## 9. Testing checklist

| Test | Expected |
|---|---|
| Add a valid dish | Saved, message shown |
| Add dish with category "snack" or negative cost | Rejected by validation |
| Log with wasted kg above prepared kg | Rejected by `$expr` rule |
| Add a dish with an existing name | Duplicate key error shown |
| Feedback with rating 6 | Rejected |
| Update cost of a dish | `modified_count` is 1 |
| Delete a log | Its feedback is also removed |
| Open every report | Non-empty, correctly sorted results |
| Open a wrong URL | Custom 404 page |

## 10. Screenshots for the report

Compass view of the three collections, each page of the website, one success and one rejected insert, one screenshot per aggregation report, and the recommendation page. Capture with **Win + Shift + S**.

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `ServerSelectionTimeoutError` | MongoDB service is not running; start it and retry |
| `ModuleNotFoundError: flask` or `pymongo` | Activate `venv`, then `pip install flask pymongo` |
| `bsonType` validation errors on insert | Send `int` for `students_served` and `rating`, and a `datetime` (not a string) for dates |
| `InvalidId` error | The id from the URL is not a valid ObjectId; use `to_object_id` inside `try/except` |
| Empty reports | Run `python setup_db.py` to reseed |

## 12. Viva quick answers

- **Why MongoDB?** Flexible documents (tags, nutrition) and powerful aggregation.
- **Embed or reference?** Embed `nutrition`; reference `dish_id` and `log_id`.
- **How is validation done?** `$jsonSchema` plus `$expr`, and a unique index.
- **What does `$lookup` do?** A left join that attaches matching documents from another collection.
- **Why `insert_many` for seeding?** One network call for many documents.
- Be ready to write a new query live, for example: `find({"hostel_block": "A", "wasted_kg": {"$gt": 10}})`.

## 13. Notes

- Seed data is simulated from realistic mess menus and quantities; adjust dishes and portions to your own hostel so the dataset is truly yours.
- Only PyMongo is used for database access (no ODM), as the task requires.
- Written for an individual submission; understand and be able to modify every file.
