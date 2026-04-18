import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import requests
import json
import re
import os
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI SQL Business Intelligence",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="collapsedControl"] { display:none; }
section[data-testid="stSidebar"]  { display:none; }
.insight { background:#1a1a2e; border-left:4px solid #2ECC71; padding:10px 16px;
           border-radius:0 8px 8px 0; margin:5px 0; font-size:14px; color:#ddd; }
.sql-box { background:#0d1117; border:1px solid #30363d; border-radius:8px;
           padding:14px 18px; font-family:monospace; font-size:13px;
           color:#79c0ff; margin:8px 0; white-space:pre-wrap; }
.card-row { display:flex; gap:14px; margin:10px 0; flex-wrap:wrap; }
.card { flex:1; min-width:130px; background:#1e1e2e; border-radius:10px;
        padding:14px 18px; border-left:4px solid #7F77DD; }
.card-val { font-size:24px; font-weight:700; color:#fff; }
.card-lbl { font-size:11px; color:#aaa; margin-top:2px; }
.author-bar { display:flex; align-items:center; gap:14px; padding:10px 0 4px 0; }
.author-bar img { border-radius:50%; width:44px; height:44px; }
.author-name { font-weight:700; color:#fff; font-size:15px; }
.author-sub  { color:#aaa; font-size:12px; }
.badge { display:inline-block; padding:3px 10px; border-radius:14px;
         font-size:11px; font-weight:600; text-decoration:none; margin-right:5px; }
.badge-gh { background:#333; color:#fff; }
.badge-li { background:#0A66C2; color:#fff; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
PAGES = ["Home", "AI Query Assistant", "Sales Dashboard", "SQL Explorer", "AI Insights"]
if "page"       not in st.session_state: st.session_state.page = "Home"
if "query_hist" not in st.session_state: st.session_state.query_hist = []
if "api_key"    not in st.session_state: st.session_state.api_key = ""

# ─────────────────────────────────────────────────────────────────────────────
# TOP NAVBAR
# ─────────────────────────────────────────────────────────────────────────────
icons = ["🏠","🤖","📊","🔍","💡"]
cols  = st.columns(len(PAGES))
for col, pg, ic in zip(cols, PAGES, icons):
    with col:
        if st.button(f"{ic} {pg}", key=f"nav_{pg}", use_container_width=True,
                     type="primary" if st.session_state.page == pg else "secondary"):
            st.session_state.page = pg
            st.rerun()

st.markdown("<hr style='margin:4px 0 16px 0;border-color:#333'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────
DB_PATH  = "superstore.db"
CSV_PATH = "superstore.csv"

GITHUB_CSV = (
    "https://raw.githubusercontent.com/SaurabhAnand56/"
    "AI-SQL-Business-Intelligence-Assistant/main/superstore.csv"
)

@st.cache_resource
def load_db():
    if not os.path.exists(DB_PATH):
        try:
            df = pd.read_csv(GITHUB_CSV)
        except Exception:
            df = pd.read_csv(CSV_PATH)
        conn = sqlite3.connect(DB_PATH)
        df.to_sql("sales", conn, if_exists="replace", index=False)
        conn.commit()
        conn.close()
    conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
    df_all = pd.read_sql("SELECT * FROM sales", conn)
    return conn, df_all

conn, df = load_db()

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA = """
Table: sales
Columns:
  order_id       TEXT    -- unique order identifier
  order_date     TEXT    -- order date (YYYY-MM-DD)
  ship_date      TEXT    -- shipment date (YYYY-MM-DD)
  ship_mode      TEXT    -- Standard Class, Second Class, First Class, Same Day
  customer_id    TEXT    -- customer identifier
  customer_name  TEXT    -- customer name
  segment        TEXT    -- Consumer, Corporate, Home Office
  state          TEXT    -- US state name
  region         TEXT    -- West, East, Central, South
  product_name   TEXT    -- product name
  category       TEXT    -- Technology, Furniture, Office Supplies
  sub_category   TEXT    -- sub-category of product
  sales          REAL    -- order sales amount in USD
  quantity       INTEGER -- quantity ordered
  discount       REAL    -- discount applied (0.0 to 0.5)
  profit         REAL    -- profit amount in USD
"""

EXAMPLE_QUESTIONS = [
    "Which region has the highest total sales?",
    "What are the top 5 most profitable products?",
    "Which product category generates the most revenue?",
    "Show monthly sales trend for 2022",
    "Which customer segment has the highest average order value?",
    "What is the average discount given per category?",
    "Which state has the lowest profit margin?",
    "How many orders were placed each year?",
    "Which ship mode is used most frequently?",
    "Show top 10 states by total sales",
]

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI API FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

def call_gemini(prompt: str, api_key: str) -> dict:
    """Call Gemini 1.5 Flash API — free tier, no credit card needed."""
    url  = f"{GEMINI_URL}?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 500,
        }
    }
    try:
        r = requests.post(url, json=body, timeout=30)
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return {"success": True, "text": text}
        else:
            err = r.json().get("error", {}).get("message", r.text[:200])
            return {"success": False, "error": err}
    except Exception as e:
        return {"success": False, "error": str(e)}


def text_to_sql(question: str, api_key: str) -> dict:
    """Convert plain English question to SQL using Gemini."""
    prompt = f"""You are an expert SQL analyst. Convert the user's question into a SQLite SQL query.

Database schema:
{SCHEMA}

Rules:
- Use only SQLite-compatible syntax
- Use strftime('%Y', order_date) to extract year
- Use strftime('%Y-%m', order_date) to extract month
- Always use ROUND(value, 2) for monetary values
- Limit results to 20 rows maximum unless asked otherwise
- Return ONLY the raw SQL query — no explanation, no markdown, no backticks, no comments

User question: {question}

SQL query:"""

    result = call_gemini(prompt, api_key)
    if not result["success"]:
        return result
    sql = result["text"]
    # Clean up any accidental markdown
    sql = re.sub(r"```sql|```", "", sql).strip()
    # Remove any lines that are not SQL
    sql_lines = [ln for ln in sql.splitlines() if ln.strip() and not ln.strip().startswith("--")]
    sql = "\n".join(sql_lines).strip()
    return {"success": True, "sql": sql}


def generate_insight(question: str, result_df: pd.DataFrame, api_key: str) -> str:
    """Generate plain English business insight from query results using Gemini."""
    preview = result_df.head(10).to_string(index=False)
    prompt  = f"""You are a business analyst. The user asked: "{question}"

Query results:
{preview}

Write 2-3 sentences of plain English business insight from these results.
Be specific — mention actual numbers from the data.
Keep it concise and actionable. No bullet points. No markdown."""

    result = call_gemini(prompt, api_key)
    return result["text"] if result["success"] else "Could not generate insight."


def run_sql(query: str):
    """Execute SQL safely and return DataFrame or error string."""
    try:
        result = pd.read_sql_query(query, conn)
        return {"success": True, "df": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def auto_chart(df_result: pd.DataFrame, question: str = ""):
    """Pick and render the best chart type for the query result."""
    if df_result is None or df_result.empty or len(df_result.columns) < 2:
        return
    num_cols = df_result.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df_result.select_dtypes(exclude=[np.number]).columns.tolist()
    if not num_cols:
        return

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    y_col = num_cols[0]
    x_col = cat_cols[0] if cat_cols else df_result.columns[0]

    if any(w in question.lower() for w in ["trend","month","year","over time","growth","daily"]):
        ax.plot(range(len(df_result)), df_result[y_col],
                marker='o', linewidth=2.5, color='#7F77DD', markersize=5)
        ax.fill_between(range(len(df_result)), df_result[y_col], alpha=0.15, color='#7F77DD')
        step = max(1, len(df_result)//8)
        ax.set_xticks(range(0, len(df_result), step))
        ax.set_xticklabels(df_result[x_col].astype(str).iloc[::step], rotation=45, ha='right', fontsize=8)
    elif len(df_result) <= 15:
        colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(df_result)))
        ax.barh(df_result[x_col].astype(str), df_result[y_col], color=colors, edgecolor='none')
        ax.set_xlabel(y_col)
        for i, val in enumerate(df_result[y_col]):
            ax.text(val * 1.01, i, f'{val:,.1f}', va='center', fontsize=9)
    else:
        ax.bar(df_result[x_col].astype(str), df_result[y_col],
               color='#7F77DD', edgecolor='none', alpha=0.85)
        plt.xticks(rotation=45, ha='right', fontsize=8)

    if question:
        ax.set_title(question[:70], fontsize=11, fontweight='bold', pad=10)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()


def clean_ax(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
pg = st.session_state.page

if pg == "Home":
    st.markdown("""
    <div class="author-bar">
        <img src="https://github.com/SaurabhAnand56.png"/>
        <div>
            <div class="author-name">Saurabh Anand</div>
            <div class="author-sub">Data Analyst &nbsp;|&nbsp; Python &bull; SQL &bull; AI &bull; Power BI</div>
            <a class="badge badge-gh" href="https://github.com/SaurabhAnand56" target="_blank">GitHub</a>
            <a class="badge badge-li" href="https://www.linkedin.com/in/saurabhanand56" target="_blank">LinkedIn</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.title("🤖 AI-Powered SQL Business Intelligence Assistant")
    st.markdown("""
    Ask business questions in **plain English** — Gemini AI converts them to SQL, runs the query
    on a real database, and explains the results.
    Built on a **9,994-row Superstore sales database**.
    """)

    total_sales  = df['sales'].sum()
    total_profit = df['profit'].sum()
    total_orders = df['order_id'].nunique()
    margin       = total_profit / total_sales * 100

    st.markdown(f"""
    <div class="card-row">
      <div class="card"><div class="card-val">${total_sales/1e6:.2f}M</div><div class="card-lbl">Total Sales</div></div>
      <div class="card"><div class="card-val">${total_profit/1e6:.2f}M</div><div class="card-lbl">Total Profit</div></div>
      <div class="card"><div class="card-val">{total_orders:,}</div><div class="card-lbl">Total Orders</div></div>
      <div class="card"><div class="card-val">{margin:.1f}%</div><div class="card-lbl">Profit Margin</div></div>
      <div class="card"><div class="card-val">{df['customer_id'].nunique():,}</div><div class="card-lbl">Customers</div></div>
      <div class="card"><div class="card-val">4</div><div class="card-lbl">Regions</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### What this app does")
    st.markdown('<div class="insight">🤖 <b>AI Query Assistant</b> — Type any question, Gemini generates SQL + chart + insight</div>', unsafe_allow_html=True)
    st.markdown('<div class="insight">📊 <b>Sales Dashboard</b> — Revenue by region, category trends, profit analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="insight">🔍 <b>SQL Explorer</b> — Write and run custom SQL with 7 preset queries</div>', unsafe_allow_html=True)
    st.markdown('<div class="insight">💡 <b>AI Insights</b> — Auto-generated full business intelligence report</div>', unsafe_allow_html=True)

    st.markdown("### Try asking the AI")
    c1, c2 = st.columns(2)
    for i, q in enumerate(EXAMPLE_QUESTIONS[:6]):
        with (c1 if i % 2 == 0 else c2):
            if st.button(q, key=f"hq_{i}", use_container_width=True):
                st.session_state.page = "AI Query Assistant"
                st.session_state.prefill_q = q
                st.rerun()

    st.markdown("### Database schema")
    st.code(SCHEMA.strip(), language="sql")

# ══════════════════════════════════════════════════════════════════════════════
# AI QUERY ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
elif pg == "AI Query Assistant":
    st.title("🤖 AI Query Assistant")
    st.markdown("Ask any business question in plain English. **Gemini AI** converts it to SQL and runs it.")

    # API Key
    with st.expander("⚙️ Enter your Gemini API Key (free)", expanded=st.session_state.api_key == ""):
        st.markdown("""
        **How to get a free Gemini API key:**
        1. Go to [aistudio.google.com](https://aistudio.google.com)
        2. Click **Get API Key** → Create API key
        3. Copy and paste it below — completely free, no credit card needed
        """)
        api_input = st.text_input("Gemini API Key", value=st.session_state.api_key,
                                   type="password", placeholder="AIza...")
        if api_input:
            st.session_state.api_key = api_input

    st.markdown("---")

    default_q = st.session_state.pop("prefill_q", "")

    col1, col2 = st.columns([3, 1])
    with col1:
        question = st.text_input("Ask a business question:", value=default_q,
                                  placeholder="e.g. Which region has the highest profit margin?")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("Ask AI →", use_container_width=True, type="primary")

    st.markdown("**Quick examples:**")
    ex_cols = st.columns(3)
    for i, q in enumerate(EXAMPLE_QUESTIONS):
        with ex_cols[i % 3]:
            if st.button(q, key=f"ex_{i}", use_container_width=True):
                question = q
                run_btn  = True

    st.markdown("---")

    if run_btn and question.strip():
        if not st.session_state.api_key:
            st.warning("Please enter your Gemini API key above. It's free — get it at aistudio.google.com")
        else:
            with st.spinner("Gemini AI is generating SQL..."):
                sql_result = text_to_sql(question, st.session_state.api_key)

            if not sql_result["success"]:
                st.error(f"AI Error: {sql_result['error']}")
            else:
                sql_query = sql_result["sql"]
                st.markdown("#### Generated SQL")
                st.markdown(f'<div class="sql-box">{sql_query}</div>', unsafe_allow_html=True)

                with st.spinner("Running query on database..."):
                    db_result = run_sql(sql_query)

                if not db_result["success"]:
                    st.error(f"SQL Error: {db_result['error']}")
                    st.info("Try rephrasing your question slightly.")
                else:
                    result_df = db_result["df"]
                    st.success(f"Query returned {len(result_df)} rows")

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("#### Results")
                        st.dataframe(result_df, use_container_width=True, hide_index=True)
                    with c2:
                        st.markdown("#### Chart")
                        auto_chart(result_df, question)

                    with st.spinner("Generating business insight..."):
                        insight = generate_insight(question, result_df, st.session_state.api_key)
                    st.markdown("#### AI Business Insight")
                    st.markdown(f'<div class="insight">💡 {insight}</div>', unsafe_allow_html=True)

                    st.session_state.query_hist.append({
                        "question": question, "sql": sql_query,
                        "rows": len(result_df), "insight": insight
                    })

    if st.session_state.query_hist:
        st.markdown("---")
        st.markdown("#### Query History")
        for h in reversed(st.session_state.query_hist[-5:]):
            with st.expander(f"Q: {h['question'][:60]}"):
                st.code(h['sql'], language="sql")
                st.caption(f"Returned {h['rows']} rows")
                st.markdown(f'<div class="insight">💡 {h["insight"]}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SALES DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif pg == "Sales Dashboard":
    st.title("📊 Sales Dashboard")
    st.markdown("Interactive business intelligence charts from the Superstore database.")

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        sel_region = st.multiselect("Region", df['region'].unique().tolist(), default=df['region'].unique().tolist())
    with fc2:
        sel_cat = st.multiselect("Category", df['category'].unique().tolist(), default=df['category'].unique().tolist())
    with fc3:
        years = sorted(pd.to_datetime(df['order_date']).dt.year.unique())
        sel_year = st.multiselect("Year", years, default=years)

    df_f = df[
        df['region'].isin(sel_region) &
        df['category'].isin(sel_cat) &
        pd.to_datetime(df['order_date']).dt.year.isin(sel_year)
    ].copy()

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Sales & Profit by Region")
        region_df = pd.read_sql_query(
            "SELECT region, ROUND(SUM(sales),2) as total_sales, ROUND(SUM(profit),2) as total_profit FROM sales GROUP BY region ORDER BY total_sales DESC",
            conn)
        fig, ax = plt.subplots(figsize=(6,4))
        x = np.arange(len(region_df)); w = 0.35
        ax.bar(x-w/2, region_df['total_sales'],  w, label='Sales',  color='#7F77DD', alpha=0.85)
        ax.bar(x+w/2, region_df['total_profit'], w, label='Profit', color='#2ECC71', alpha=0.85)
        ax.set_xticks(x); ax.set_xticklabels(region_df['region'])
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x/1000:.0f}K'))
        ax.legend(); clean_ax(ax)
        st.pyplot(fig); plt.close()

    with c2:
        st.markdown("#### Sales by Category")
        cat_df = df_f.groupby('category')['sales'].sum().reset_index().sort_values('sales', ascending=False)
        fig, ax = plt.subplots(figsize=(6,4))
        wedges, texts, autotexts = ax.pie(
            cat_df['sales'], labels=cat_df['category'], autopct='%1.1f%%',
            colors=['#7F77DD','#2ECC71','#E74C3C'], startangle=90,
            wedgeprops=dict(edgecolor='white', linewidth=1.5))
        for t in autotexts: t.set_fontsize(10); t.set_fontweight('bold')
        st.pyplot(fig); plt.close()

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### Monthly Sales Trend")
        df_f['month'] = pd.to_datetime(df_f['order_date']).dt.to_period('M').astype(str)
        monthly = df_f.groupby('month')['sales'].sum().reset_index().tail(24)
        fig, ax = plt.subplots(figsize=(6,4))
        ax.plot(range(len(monthly)), monthly['sales'], color='#7F77DD', linewidth=2.5, marker='o', markersize=3)
        ax.fill_between(range(len(monthly)), monthly['sales'], alpha=0.15, color='#7F77DD')
        step = max(1, len(monthly)//6)
        ax.set_xticks(range(0, len(monthly), step))
        ax.set_xticklabels(monthly['month'].iloc[::step], rotation=45, ha='right', fontsize=8)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x/1000:.0f}K'))
        clean_ax(ax); st.pyplot(fig); plt.close()

    with c4:
        st.markdown("#### Profit by Sub-Category")
        sub_df = pd.read_sql_query(
            "SELECT sub_category, ROUND(SUM(profit),2) as profit FROM sales GROUP BY sub_category ORDER BY profit DESC LIMIT 10",
            conn)
        fig, ax = plt.subplots(figsize=(6,4))
        colors_bar = ['#2ECC71' if v >= 0 else '#E74C3C' for v in sub_df['profit']]
        ax.barh(sub_df['sub_category'], sub_df['profit'], color=colors_bar, edgecolor='none')
        ax.axvline(0, color='white', linewidth=0.8); ax.set_xlabel("Profit (USD)"); clean_ax(ax)
        st.pyplot(fig); plt.close()

    c5, c6 = st.columns(2)
    with c5:
        st.markdown("#### Top 10 States by Sales")
        state_df = pd.read_sql_query(
            "SELECT state, ROUND(SUM(sales),2) as sales FROM sales GROUP BY state ORDER BY sales DESC LIMIT 10",
            conn)
        fig, ax = plt.subplots(figsize=(6,5))
        colors2 = plt.cm.Blues(np.linspace(0.4, 0.9, len(state_df)))[::-1]
        ax.barh(state_df['state'][::-1], state_df['sales'][::-1], color=colors2[::-1], edgecolor='none')
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x/1000:.0f}K'))
        clean_ax(ax); st.pyplot(fig); plt.close()

    with c6:
        st.markdown("#### Discount vs Profit")
        sample = df_f.sample(min(500, len(df_f)), random_state=42)
        fig, ax = plt.subplots(figsize=(6,5))
        sc = ax.scatter(sample['discount'], sample['profit'],
                        c=sample['sales'], cmap='RdYlGn', alpha=0.5, s=20)
        plt.colorbar(sc, ax=ax, label='Sales')
        ax.axhline(0, color='red', linestyle='--', linewidth=1, alpha=0.7)
        ax.set_xlabel("Discount"); ax.set_ylabel("Profit"); clean_ax(ax)
        st.pyplot(fig); plt.close()
        st.info("High discounts (>0.3) consistently result in negative profit.")

# ══════════════════════════════════════════════════════════════════════════════
# SQL EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
elif pg == "SQL Explorer":
    st.title("🔍 SQL Explorer")
    st.markdown("Write and run your own SQL queries on the Superstore database.")

    with st.expander("View schema"):
        st.code(SCHEMA.strip(), language="sql")

    PRESET_QUERIES = {
        "Select preset query...": "",
        "Top 10 products by revenue":   "SELECT product_name, ROUND(SUM(sales),2) as total_sales\nFROM sales\nGROUP BY product_name\nORDER BY total_sales DESC\nLIMIT 10;",
        "Profit margin by category":    "SELECT category,\n  ROUND(SUM(sales),2) as total_sales,\n  ROUND(SUM(profit),2) as total_profit,\n  ROUND(SUM(profit)/SUM(sales)*100, 2) as profit_margin_pct\nFROM sales\nGROUP BY category\nORDER BY profit_margin_pct DESC;",
        "Monthly sales 2022":           "SELECT strftime('%Y-%m', order_date) as month,\n  ROUND(SUM(sales),2) as monthly_sales,\n  COUNT(*) as orders\nFROM sales\nWHERE strftime('%Y', order_date) = '2022'\nGROUP BY month\nORDER BY month;",
        "Region segment analysis":      "SELECT region, segment,\n  ROUND(SUM(sales),2) as sales,\n  ROUND(AVG(sales),2) as avg_order_value\nFROM sales\nGROUP BY region, segment\nORDER BY region, sales DESC;",
        "High discount loss orders":    "SELECT order_id, product_name, category,\n  ROUND(sales,2) as sales,\n  discount,\n  ROUND(profit,2) as profit\nFROM sales\nWHERE discount >= 0.4 AND profit < 0\nORDER BY profit ASC\nLIMIT 15;",
        "Year over year growth":        "SELECT strftime('%Y', order_date) as year,\n  ROUND(SUM(sales),2) as total_sales,\n  COUNT(DISTINCT order_id) as orders,\n  ROUND(AVG(sales),2) as avg_order_value\nFROM sales\nGROUP BY year\nORDER BY year;",
        "Window: running total sales":  "SELECT order_date,\n  ROUND(SUM(sales),2) as daily_sales,\n  ROUND(SUM(SUM(sales)) OVER (ORDER BY order_date),2) as running_total\nFROM sales\nGROUP BY order_date\nORDER BY order_date\nLIMIT 30;",
    }

    preset = st.selectbox("Choose a preset query:", list(PRESET_QUERIES.keys()))
    default_sql = PRESET_QUERIES[preset] if preset != "Select preset query..." else \
        "SELECT category, ROUND(SUM(sales),2) as total_sales,\n  ROUND(SUM(profit),2) as total_profit\nFROM sales\nGROUP BY category\nORDER BY total_sales DESC;"

    user_sql = st.text_area("SQL Query:", value=default_sql, height=160)

    if st.button("Run Query ▶", type="primary"):
        if user_sql.strip():
            result = run_sql(user_sql)
            if result["success"]:
                res_df = result["df"]
                st.success(f"Returned {len(res_df)} rows, {len(res_df.columns)} columns")
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                auto_chart(res_df, preset if preset != "Select preset query..." else "")
                csv = res_df.to_csv(index=False)
                st.download_button("Download CSV", csv, "query_result.csv", "text/csv")
            else:
                st.error(f"SQL Error: {result['error']}")

# ══════════════════════════════════════════════════════════════════════════════
# AI INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
elif pg == "AI Insights":
    st.title("💡 AI Business Insights")
    st.markdown("Auto-generated business intelligence report powered by **Gemini AI**.")

    with st.expander("⚙️ Gemini API Key", expanded=st.session_state.api_key == ""):
        st.markdown("Get your free key at [aistudio.google.com](https://aistudio.google.com)")
        api_input = st.text_input("API Key", value=st.session_state.api_key,
                                   type="password", placeholder="AIza...")
        if api_input:
            st.session_state.api_key = api_input

    st.markdown("---")

    insight_queries = {
        "Revenue by Region":    "SELECT region, ROUND(SUM(sales),2) as sales, ROUND(SUM(profit),2) as profit FROM sales GROUP BY region ORDER BY sales DESC",
        "Category Performance": "SELECT category, ROUND(SUM(sales),2) as sales, ROUND(SUM(profit),2) as profit, ROUND(SUM(profit)/SUM(sales)*100,2) as margin_pct FROM sales GROUP BY category",
        "Yearly Growth":        "SELECT strftime('%Y',order_date) as year, ROUND(SUM(sales),2) as sales, COUNT(*) as orders FROM sales GROUP BY year ORDER BY year",
        "Discount Impact":      "SELECT CASE WHEN discount=0 THEN 'No discount' WHEN discount<=0.2 THEN 'Low (<=20%)' WHEN discount<=0.4 THEN 'Medium (21-40%)' ELSE 'High (>40%)' END as discount_band, ROUND(AVG(profit),2) as avg_profit, COUNT(*) as orders FROM sales GROUP BY discount_band ORDER BY avg_profit DESC",
        "Segment Analysis":     "SELECT segment, ROUND(SUM(sales),2) as sales, ROUND(AVG(sales),2) as avg_order, COUNT(DISTINCT customer_id) as customers FROM sales GROUP BY segment ORDER BY sales DESC",
    }

    results_cache = {}
    for title, q in insight_queries.items():
        result = run_sql(q)
        if result["success"]:
            results_cache[title] = result["df"]

    if st.button("Generate Full AI Report", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.warning("Please enter your Gemini API key above. Free at aistudio.google.com")
        else:
            for title, res_df in results_cache.items():
                with st.spinner(f"Analysing {title}..."):
                    insight = generate_insight(title, res_df, st.session_state.api_key)
                st.markdown(f"#### {title}")
                c1, c2 = st.columns(2)
                with c1: st.dataframe(res_df, use_container_width=True, hide_index=True)
                with c2: auto_chart(res_df, title)
                st.markdown(f'<div class="insight">💡 {insight}</div>', unsafe_allow_html=True)
                st.markdown("---")
    else:
        st.info("Click 'Generate Full AI Report' to add Gemini AI insights. Showing charts:")
        for title, res_df in results_cache.items():
            st.markdown(f"#### {title}")
            c1, c2 = st.columns(2)
            with c1: st.dataframe(res_df, use_container_width=True, hide_index=True)
            with c2: auto_chart(res_df, title)
            st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#888;font-size:12px;padding:6px 0'>
    Built by <b>Saurabh Anand</b> &nbsp;|&nbsp;
    <a href='https://github.com/SaurabhAnand56' target='_blank' style='color:#aaa'>GitHub</a> &nbsp;|&nbsp;
    <a href='https://www.linkedin.com/in/saurabhanand56' target='_blank' style='color:#aaa'>LinkedIn</a> &nbsp;|&nbsp;
    AI: Gemini 2.5 Flash (Free) &nbsp;|&nbsp; DB: SQLite &nbsp;|&nbsp; 9,994 orders
</div>
""", unsafe_allow_html=True)
