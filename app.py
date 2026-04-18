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
.topbar { display:flex; align-items:center; gap:8px; padding:8px 0 14px 0; flex-wrap:wrap; }
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
if "page"        not in st.session_state: st.session_state.page = "Home"
if "query_hist"  not in st.session_state: st.session_state.query_hist = []
if "api_key"     not in st.session_state: st.session_state.api_key = ""

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

@st.cache_data
def load_db():
    # Try local first, then GitHub
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
# DATABASE SCHEMA STRING
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
# AI: TEXT → SQL
# ─────────────────────────────────────────────────────────────────────────────
def text_to_sql(question: str, api_key: str) -> dict:
    """Call Claude API to convert natural language to SQL."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    prompt = f"""You are an expert SQL analyst. Convert the user's question into a SQLite SQL query.

Database schema:
{SCHEMA}

Rules:
- Use only SQLite-compatible syntax
- Use strftime('%Y', order_date) for year extraction
- Use strftime('%Y-%m', order_date) for month extraction
- Always use ROUND(value, 2) for monetary values
- Limit results to 20 rows maximum unless asked for more
- Return ONLY valid SQL — no explanation, no markdown, no backticks
- Column names are case-sensitive — use exact names from schema

User question: {question}

SQL query:"""

    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers=headers, json=body, timeout=30)
        if r.status_code == 200:
            sql = r.json()["content"][0]["text"].strip()
            sql = re.sub(r"```sql|```", "", sql).strip()
            return {"success": True, "sql": sql}
        else:
            return {"success": False, "error": f"API error {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_insight(question: str, result_df: pd.DataFrame, api_key: str) -> str:
    """Generate a plain English insight from query results."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    preview = result_df.head(10).to_string(index=False)
    prompt  = f"""You are a business analyst. The user asked: "{question}"

Query results (top 10 rows):
{preview}

Write 2-3 sentences of plain English business insight from these results.
Be specific — mention actual numbers, categories, or patterns you see.
Keep it concise and actionable. No bullet points."""

    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers=headers, json=body, timeout=30)
        if r.status_code == 200:
            return r.json()["content"][0]["text"].strip()
        return "Could not generate insight."
    except:
        return "Could not generate insight."


def run_sql(query: str):
    """Execute SQL and return DataFrame or error."""
    try:
        result = pd.read_sql_query(query, conn)
        return {"success": True, "df": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def auto_chart(df_result: pd.DataFrame, question: str):
    """Automatically choose and render the best chart for the result."""
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

    # Time series
    if any(w in question.lower() for w in ["trend","month","year","over time","daily"]):
        ax.plot(df_result[x_col].astype(str), df_result[y_col],
                marker='o', linewidth=2.5, color='#7F77DD', markersize=5)
        ax.fill_between(range(len(df_result)), df_result[y_col], alpha=0.15, color='#7F77DD')
        plt.xticks(range(len(df_result)), df_result[x_col].astype(str), rotation=45, ha='right', fontsize=8)

    # Horizontal bar for rankings/comparisons
    elif len(df_result) <= 15:
        colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(df_result)))
        ax.barh(df_result[x_col].astype(str), df_result[y_col],
                color=colors, edgecolor='none')
        ax.set_xlabel(y_col)
        for i, (val, label) in enumerate(zip(df_result[y_col], df_result[x_col])):
            ax.text(val * 1.01, i, f'{val:,.1f}', va='center', fontsize=9)

    # Vertical bar
    else:
        ax.bar(df_result[x_col].astype(str), df_result[y_col],
               color='#7F77DD', edgecolor='none', alpha=0.85)
        plt.xticks(rotation=45, ha='right', fontsize=8)

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
    # Author
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
    Ask business questions in **plain English** — AI converts them to SQL, runs the query,
    and explains the results. Built on a **9,994-row Superstore sales database** with
    real SQL queries, AI insights, and interactive dashboards.
    """)

    # Metrics
    total_sales   = df['sales'].sum()
    total_profit  = df['profit'].sum()
    total_orders  = df['order_id'].nunique()
    profit_margin = (total_profit / total_sales * 100)
    st.markdown(f"""
    <div class="card-row">
      <div class="card"><div class="card-val">${total_sales/1e6:.2f}M</div><div class="card-lbl">Total Sales</div></div>
      <div class="card"><div class="card-val">${total_profit/1e6:.2f}M</div><div class="card-lbl">Total Profit</div></div>
      <div class="card"><div class="card-val">{total_orders:,}</div><div class="card-lbl">Total Orders</div></div>
      <div class="card"><div class="card-val">{profit_margin:.1f}%</div><div class="card-lbl">Profit Margin</div></div>
      <div class="card"><div class="card-val">{df['customer_id'].nunique():,}</div><div class="card-lbl">Customers</div></div>
      <div class="card"><div class="card-val">4</div><div class="card-lbl">Regions</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### What this app does")
    st.markdown('<div class="insight">🤖 <b>AI Query Assistant</b> — Type any business question, get SQL + chart + insight instantly</div>', unsafe_allow_html=True)
    st.markdown('<div class="insight">📊 <b>Sales Dashboard</b> — Interactive charts: revenue by region, category trends, profit analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="insight">🔍 <b>SQL Explorer</b> — Write and run your own SQL queries with live results</div>', unsafe_allow_html=True)
    st.markdown('<div class="insight">💡 <b>AI Insights</b> — Auto-generated business intelligence report from the database</div>', unsafe_allow_html=True)

    st.markdown("### Try asking the AI")
    cols2 = st.columns(2)
    for i, q in enumerate(EXAMPLE_QUESTIONS[:6]):
        with cols2[i % 2]:
            if st.button(q, key=f"eq_{i}", use_container_width=True):
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
    st.markdown("Ask any business question in plain English. AI converts it to SQL and runs it.")

    # API key input
    with st.expander("⚙️ Enter your Anthropic API Key", expanded=st.session_state.api_key == ""):
        api_input = st.text_input("API Key", value=st.session_state.api_key,
                                   type="password", placeholder="sk-ant-...")
        if api_input:
            st.session_state.api_key = api_input
        st.caption("Get a free API key at console.anthropic.com — key is never stored or logged.")

    st.markdown("---")

    # Prefill from home page quick questions
    default_q = st.session_state.pop("prefill_q", "")

    col1, col2 = st.columns([3, 1])
    with col1:
        question = st.text_input("Ask a business question:", value=default_q,
                                  placeholder="e.g. Which region has the highest profit?")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("Ask AI →", use_container_width=True, type="primary")

    # Example questions
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
            st.warning("Please enter your Anthropic API key above to use AI features.")
        else:
            with st.spinner("AI is generating SQL..."):
                sql_result = text_to_sql(question, st.session_state.api_key)

            if not sql_result["success"]:
                st.error(f"AI Error: {sql_result['error']}")
            else:
                sql_query = sql_result["sql"]

                st.markdown("#### Generated SQL")
                st.markdown(f'<div class="sql-box">{sql_query}</div>', unsafe_allow_html=True)

                with st.spinner("Running query..."):
                    db_result = run_sql(sql_query)

                if not db_result["success"]:
                    st.error(f"SQL Error: {db_result['error']}")
                    st.info("Try rephrasing your question.")
                else:
                    result_df = db_result["df"]
                    st.success(f"Query returned {len(result_df)} rows")

                    c1, c2 = st.columns([1, 1])
                    with c1:
                        st.markdown("#### Results")
                        st.dataframe(result_df, use_container_width=True, hide_index=True)

                    with c2:
                        st.markdown("#### Chart")
                        auto_chart(result_df, question)

                    # AI Insight
                    with st.spinner("Generating business insight..."):
                        insight = generate_insight(question, result_df, st.session_state.api_key)
                    st.markdown("#### AI Business Insight")
                    st.markdown(f'<div class="insight">💡 {insight}</div>', unsafe_allow_html=True)

                    # Save to history
                    st.session_state.query_hist.append({
                        "question": question, "sql": sql_query,
                        "rows": len(result_df), "insight": insight
                    })

    # Query history
    if st.session_state.query_hist:
        st.markdown("---")
        st.markdown("#### Query History")
        for i, h in enumerate(reversed(st.session_state.query_hist[-5:])):
            with st.expander(f"Q: {h['question'][:60]}..."):
                st.code(h['sql'], language="sql")
                st.caption(f"Returned {h['rows']} rows")
                st.markdown(f'<div class="insight">💡 {h["insight"]}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SALES DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif pg == "Sales Dashboard":
    st.title("📊 Sales Dashboard")
    st.markdown("Interactive business intelligence charts from the Superstore database.")

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        sel_region = st.multiselect("Region", df['region'].unique().tolist(),
                                     default=df['region'].unique().tolist())
    with fc2:
        sel_cat = st.multiselect("Category", df['category'].unique().tolist(),
                                  default=df['category'].unique().tolist())
    with fc3:
        years = sorted(pd.to_datetime(df['order_date']).dt.year.unique())
        sel_year = st.multiselect("Year", years, default=years)

    df_f = df[
        df['region'].isin(sel_region) &
        df['category'].isin(sel_cat) &
        pd.to_datetime(df['order_date']).dt.year.isin(sel_year)
    ].copy()

    st.markdown("---")

    # Row 1
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Sales by Region")
        q = "SELECT region, ROUND(SUM(sales),2) as total_sales, ROUND(SUM(profit),2) as total_profit FROM sales GROUP BY region ORDER BY total_sales DESC"
        region_df = pd.read_sql_query(q, conn)
        fig, ax = plt.subplots(figsize=(6,4))
        x = np.arange(len(region_df))
        w = 0.35
        ax.bar(x-w/2, region_df['total_sales'],   w, label='Sales',  color='#7F77DD', alpha=0.85)
        ax.bar(x+w/2, region_df['total_profit'],  w, label='Profit', color='#2ECC71', alpha=0.85)
        ax.set_xticks(x); ax.set_xticklabels(region_df['region'])
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x/1000:.0f}K'))
        ax.legend(); clean_ax(ax)
        st.pyplot(fig); plt.close()

    with c2:
        st.markdown("#### Sales by Category")
        cat_df = df_f.groupby('category')['sales'].sum().reset_index().sort_values('sales', ascending=False)
        fig, ax = plt.subplots(figsize=(6,4))
        colors = ['#7F77DD','#2ECC71','#E74C3C']
        wedges, texts, autotexts = ax.pie(cat_df['sales'], labels=cat_df['category'],
                                           autopct='%1.1f%%', colors=colors,
                                           startangle=90, wedgeprops=dict(edgecolor='white', linewidth=1.5))
        for t in autotexts: t.set_fontsize(10); t.set_fontweight('bold')
        st.pyplot(fig); plt.close()

    # Row 2
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### Monthly Sales Trend")
        df_f['month'] = pd.to_datetime(df_f['order_date']).dt.to_period('M').astype(str)
        monthly = df_f.groupby('month')['sales'].sum().reset_index()
        monthly = monthly.tail(24)
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
        ax.axvline(0, color='white', linewidth=0.8)
        ax.set_xlabel("Profit (USD)"); clean_ax(ax)
        st.pyplot(fig); plt.close()

    # Row 3
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
        st.markdown("#### Discount vs Profit Relationship")
        sample = df_f.sample(min(500, len(df_f)), random_state=42)
        fig, ax = plt.subplots(figsize=(6,5))
        scatter = ax.scatter(sample['discount'], sample['profit'],
                             c=sample['sales'], cmap='RdYlGn', alpha=0.5, s=20)
        plt.colorbar(scatter, ax=ax, label='Sales')
        ax.axhline(0, color='red', linestyle='--', linewidth=1, alpha=0.7)
        ax.set_xlabel("Discount"); ax.set_ylabel("Profit")
        clean_ax(ax)
        st.pyplot(fig); plt.close()
        st.info("High discounts (>0.3) consistently result in negative profit — key business risk.")

# ══════════════════════════════════════════════════════════════════════════════
# SQL EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
elif pg == "SQL Explorer":
    st.title("🔍 SQL Explorer")
    st.markdown("Write and run your own SQL queries directly on the Superstore database.")

    st.markdown("#### Database schema reference")
    with st.expander("View schema"):
        st.code(SCHEMA.strip(), language="sql")

    PRESET_QUERIES = {
        "Select preset query...": "",
        "Top 10 products by revenue": "SELECT product_name, ROUND(SUM(sales),2) as total_sales\nFROM sales\nGROUP BY product_name\nORDER BY total_sales DESC\nLIMIT 10;",
        "Profit margin by category": "SELECT category,\n  ROUND(SUM(sales),2) as total_sales,\n  ROUND(SUM(profit),2) as total_profit,\n  ROUND(SUM(profit)/SUM(sales)*100, 2) as profit_margin_pct\nFROM sales\nGROUP BY category\nORDER BY profit_margin_pct DESC;",
        "Monthly sales 2022": "SELECT strftime('%Y-%m', order_date) as month,\n  ROUND(SUM(sales),2) as monthly_sales,\n  COUNT(*) as orders\nFROM sales\nWHERE strftime('%Y', order_date) = '2022'\nGROUP BY month\nORDER BY month;",
        "Region segment analysis": "SELECT region, segment,\n  ROUND(SUM(sales),2) as sales,\n  ROUND(AVG(sales),2) as avg_order_value\nFROM sales\nGROUP BY region, segment\nORDER BY region, sales DESC;",
        "High discount low profit orders": "SELECT order_id, product_name, category,\n  ROUND(sales,2) as sales,\n  ROUND(discount,2) as discount,\n  ROUND(profit,2) as profit\nFROM sales\nWHERE discount >= 0.4 AND profit < 0\nORDER BY profit ASC\nLIMIT 15;",
        "Year over year growth": "SELECT strftime('%Y', order_date) as year,\n  ROUND(SUM(sales),2) as total_sales,\n  COUNT(DISTINCT order_id) as orders,\n  ROUND(AVG(sales),2) as avg_order_value\nFROM sales\nGROUP BY year\nORDER BY year;",
        "Window function: running total": "SELECT order_date,\n  ROUND(SUM(sales),2) as daily_sales,\n  ROUND(SUM(SUM(sales)) OVER (ORDER BY order_date),2) as running_total\nFROM sales\nGROUP BY order_date\nORDER BY order_date\nLIMIT 30;",
    }

    preset = st.selectbox("Or choose a preset query:", list(PRESET_QUERIES.keys()))
    default_sql = PRESET_QUERIES[preset] if preset != "Select preset query..." else \
        "SELECT category, ROUND(SUM(sales),2) as total_sales,\n  ROUND(SUM(profit),2) as total_profit\nFROM sales\nGROUP BY category\nORDER BY total_sales DESC;"

    user_sql = st.text_area("SQL Query:", value=default_sql, height=160,
                             placeholder="Write your SQL here...")

    if st.button("Run Query ▶", type="primary"):
        if user_sql.strip():
            result = run_sql(user_sql)
            if result["success"]:
                res_df = result["df"]
                st.success(f"Query returned {len(res_df)} rows, {len(res_df.columns)} columns")
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                auto_chart(res_df, preset if preset != "Select preset query..." else "")
                if len(res_df) > 0:
                    csv = res_df.to_csv(index=False)
                    st.download_button("Download CSV", csv, "query_result.csv", "text/csv")
            else:
                st.error(f"SQL Error: {result['error']}")
                st.info("Check your syntax — use double quotes for column aliases with spaces.")

# ══════════════════════════════════════════════════════════════════════════════
# AI INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
elif pg == "AI Insights":
    st.title("💡 AI Business Insights")
    st.markdown("Auto-generated business intelligence report powered by Claude AI.")

    with st.expander("⚙️ API Key", expanded=st.session_state.api_key == ""):
        api_input = st.text_input("Anthropic API Key", value=st.session_state.api_key,
                                   type="password", placeholder="sk-ant-...")
        if api_input:
            st.session_state.api_key = api_input

    st.markdown("---")

    # Pre-run key SQL queries
    queries = {
        "Revenue by Region":    "SELECT region, ROUND(SUM(sales),2) as sales, ROUND(SUM(profit),2) as profit FROM sales GROUP BY region ORDER BY sales DESC",
        "Category Performance": "SELECT category, ROUND(SUM(sales),2) as sales, ROUND(SUM(profit),2) as profit, ROUND(SUM(profit)/SUM(sales)*100,2) as margin_pct FROM sales GROUP BY category",
        "Yearly Growth":        "SELECT strftime('%Y',order_date) as year, ROUND(SUM(sales),2) as sales, COUNT(*) as orders FROM sales GROUP BY year ORDER BY year",
        "Discount Impact":      "SELECT CASE WHEN discount=0 THEN 'No discount' WHEN discount<=0.2 THEN 'Low (<=20%)' WHEN discount<=0.4 THEN 'Medium (<=40%)' ELSE 'High (>40%)' END as discount_band, ROUND(AVG(profit),2) as avg_profit, COUNT(*) as orders FROM sales GROUP BY discount_band",
        "Top Customers":        "SELECT customer_id, ROUND(SUM(sales),2) as total_spent, COUNT(*) as orders FROM sales GROUP BY customer_id ORDER BY total_spent DESC LIMIT 5",
    }

    results_cache = {}
    for title, q in queries.items():
        r = run_sql(q)
        if r["success"]:
            results_cache[title] = r["df"]

    if st.button("Generate Full AI Report", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.warning("Please enter your Anthropic API key above.")
        else:
            for title, res_df in results_cache.items():
                with st.spinner(f"Analysing {title}..."):
                    insight = generate_insight(title, res_df, st.session_state.api_key)
                st.markdown(f"#### {title}")
                c1, c2 = st.columns([1,1])
                with c1:
                    st.dataframe(res_df, use_container_width=True, hide_index=True)
                with c2:
                    auto_chart(res_df, title)
                st.markdown(f'<div class="insight">💡 {insight}</div>', unsafe_allow_html=True)
                st.markdown("---")
    else:
        # Show static charts without AI
        st.info("Click 'Generate Full AI Report' to add AI-powered insights to each chart. Showing charts now:")
        for title, res_df in results_cache.items():
            st.markdown(f"#### {title}")
            c1, c2 = st.columns([1,1])
            with c1:
                st.dataframe(res_df, use_container_width=True, hide_index=True)
            with c2:
                auto_chart(res_df, title)
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
    AI: Claude API &nbsp;|&nbsp; DB: SQLite &nbsp;|&nbsp; Dataset: 9,994 orders
</div>
""", unsafe_allow_html=True)
