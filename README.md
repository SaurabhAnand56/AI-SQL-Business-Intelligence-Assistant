# 🤖 AI-Powered SQL Business Intelligence Assistant

> Ask business questions in plain English → AI generates SQL → results + charts + insights

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-4285F4?logo=google)](https://ai.google.dev)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite)](https://sqlite.org)
[![GitHub](https://img.shields.io/badge/GitHub-SaurabhAnand56-181717?logo=github)](https://github.com/SaurabhAnand56)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-saurabhanand56-0A66C2?logo=linkedin)](https://www.linkedin.com/in/saurabhanand56)

---

## 🔴 Live Demo

| Demo | Link |
|------|------|
| 🚀 **Streamlit App** | *(add after deploying)* |

---

## 📌 What This Project Does

A user types: *"Which region has the highest profit margin?"*

The app:
1. Sends the question to **Gemini AI API**
2. AI generates a valid **SQL query**
3. Query runs on a **SQLite database** (9,994 orders)
4. Results displayed as **table + auto chart**
5. AI generates a **plain English business insight**

---

## 🗂️ Project Structure

```
AI-SQL-Business-Intelligence-Assistant/
│
├── app.py              # Main Streamlit application (4 pages)
├── superstore.csv      # Superstore sales dataset (9,994 rows)
├── superstore.db       # SQLite database (auto-created from CSV)
├── requirements.txt    # Python dependencies
└── README.md
```

---

## 📁 Dataset

| Property | Value |
|----------|-------|
| Rows | 9,994 orders |
| Columns | 16 features |
| Period | 2020 – 2023 |
| Source | Superstore Sales (Kaggle) |

### Columns

| Column | Type | Description |
|--------|------|-------------|
| `order_id` | TEXT | Unique order identifier |
| `order_date` | TEXT | Order date (YYYY-MM-DD) |
| `ship_mode` | TEXT | Standard / Second / First / Same Day |
| `segment` | TEXT | Consumer / Corporate / Home Office |
| `region` | TEXT | West / East / Central / South |
| `category` | TEXT | Technology / Furniture / Office Supplies |
| `sub_category` | TEXT | Product sub-category |
| `sales` | REAL | Sales amount (USD) |
| `quantity` | INT | Units ordered |
| `discount` | REAL | Discount rate (0.0–0.5) |
| `profit` | REAL | Profit amount (USD) |

---

## 🌐 App Pages

| Page | Description |
|------|-------------|
| 🏠 **Home** | Project overview, key metrics, quick question launcher |
| 🤖 **AI Query Assistant** | Natural language → SQL → chart → AI insight |
| 📊 **Sales Dashboard** | Pre-built interactive charts with region/category filters |
| 🔍 **SQL Explorer** | Write and run custom SQL with preset query library |
| 💡 **AI Insights** | Auto-generated full business intelligence report |

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| Gemini AI API | Natural language to SQL conversion + insight generation |
| SQLite | Relational database for all queries |
| SQL | Window functions, CTEs, GROUP BY, JOINs, aggregations |
| Pandas | Data manipulation |
| Matplotlib / Seaborn | Visualisations |
| Streamlit | Web app + deployment |

---

## 🚀 Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/SaurabhAnand56/AI-SQL-Business-Intelligence-Assistant.git
cd AI-SQL-Business-Intelligence-Assistant

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

Get a free Anthropic API key at **console.anthropic.com** and enter it in the app.

---

## 🔍 SQL Examples Used

```sql
-- Year-over-year growth
SELECT strftime('%Y', order_date) as year,
  ROUND(SUM(sales), 2) as total_sales,
  COUNT(DISTINCT order_id) as orders
FROM sales
GROUP BY year ORDER BY year;

-- Profit margin by category
SELECT category,
  ROUND(SUM(profit)/SUM(sales)*100, 2) as margin_pct
FROM sales GROUP BY category;

-- Window function: running total
SELECT order_date,
  ROUND(SUM(SUM(sales)) OVER (ORDER BY order_date), 2) as running_total
FROM sales GROUP BY order_date ORDER BY order_date;
```

---

## 📬 Connect

[![GitHub](https://img.shields.io/badge/GitHub-SaurabhAnand56-181717?logo=github&style=for-the-badge)](https://github.com/SaurabhAnand56)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-saurabhanand56-0A66C2?logo=linkedin&style=for-the-badge)](https://www.linkedin.com/in/saurabhanand56)
