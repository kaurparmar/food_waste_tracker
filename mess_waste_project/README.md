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
