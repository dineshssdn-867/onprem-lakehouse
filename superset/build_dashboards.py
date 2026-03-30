"""
Build Superset dashboards via REST API for the Lakehouse project.
Run via: docker exec superset python /app/build_dashboards.py
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8088"
DB_ID = 1  # Lakehouse (Trino)

# ---------- Auth ----------
def get_token():
    r = requests.post(f"{BASE_URL}/api/v1/security/login", json={
        "username": "admin", "password": "admin123",
        "provider": "db", "refresh": True
    })
    r.raise_for_status()
    return r.json()["access_token"]

def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ---------- Helpers ----------
def get_csrf(token):
    r = requests.get(f"{BASE_URL}/api/v1/security/csrf_token/", headers=headers(token))
    return r.json()["result"]

def create_dataset(token, table_name, schema):
    """Create a dataset (physical table) in Superset."""
    h = headers(token)
    # Check if already exists
    r = requests.get(f"{BASE_URL}/api/v1/dataset/", headers=h,
                     params={"q": json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": table_name}]})})
    existing = r.json().get("result", [])
    for ds in existing:
        if ds.get("schema") == schema:
            print(f"  Dataset '{schema}.{table_name}' already exists (id={ds['id']})")
            return ds["id"]

    payload = {
        "database": DB_ID,
        "schema": schema,
        "table_name": table_name,
    }
    r = requests.post(f"{BASE_URL}/api/v1/dataset/", headers=h, json=payload)
    if r.status_code == 422:
        # May already exist with different filter match
        print(f"  Dataset '{schema}.{table_name}' may already exist: {r.json()}")
        # Try to find it
        r2 = requests.get(f"{BASE_URL}/api/v1/dataset/", headers=h)
        for ds in r2.json().get("result", []):
            if ds.get("table_name") == table_name and ds.get("schema") == schema:
                return ds["id"]
        return None
    r.raise_for_status()
    ds_id = r.json()["id"]
    print(f"  Created dataset '{schema}.{table_name}' (id={ds_id})")
    return ds_id


def create_sql_dataset(token, sql, name, schema="dev_gold"):
    """Create a virtual (SQL) dataset."""
    h = headers(token)
    # Check existing
    r = requests.get(f"{BASE_URL}/api/v1/dataset/", headers=h,
                     params={"q": json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": name}]})})
    for ds in r.json().get("result", []):
        if ds.get("table_name") == name:
            print(f"  SQL dataset '{name}' already exists (id={ds['id']})")
            return ds["id"]

    payload = {
        "database": DB_ID,
        "schema": schema,
        "table_name": name,
        "sql": sql,
    }
    r = requests.post(f"{BASE_URL}/api/v1/dataset/", headers=h, json=payload)
    if r.status_code in (422, 409):
        print(f"  SQL dataset '{name}' may already exist: {r.text}")
        return None
    r.raise_for_status()
    ds_id = r.json()["id"]
    print(f"  Created SQL dataset '{name}' (id={ds_id})")
    return ds_id


def create_chart(token, name, ds_id, viz_type, params, dashboards=None):
    """Create a chart (slice) in Superset, optionally linking to dashboards."""
    h = headers(token)
    # Check existing
    r = requests.get(f"{BASE_URL}/api/v1/chart/", headers=h,
                     params={"q": json.dumps({"filters": [{"col": "slice_name", "opr": "eq", "value": name}]})})
    for ch in r.json().get("result", []):
        if ch.get("slice_name") == name:
            print(f"  Chart '{name}' already exists (id={ch['id']})")
            return ch["id"]

    payload = {
        "slice_name": name,
        "datasource_id": ds_id,
        "datasource_type": "table",
        "viz_type": viz_type,
        "params": json.dumps(params),
    }
    if dashboards:
        payload["dashboards"] = dashboards
    r = requests.post(f"{BASE_URL}/api/v1/chart/", headers=h, json=payload)
    r.raise_for_status()
    chart_id = r.json()["id"]
    print(f"  Created chart '{name}' (id={chart_id})")
    return chart_id


def create_dashboard(token, name, slug):
    """Create a dashboard."""
    h = headers(token)
    r = requests.get(f"{BASE_URL}/api/v1/dashboard/", headers=h,
                     params={"q": json.dumps({"filters": [{"col": "slug", "opr": "eq", "value": slug}]})})
    for d in r.json().get("result", []):
        if d.get("slug") == slug:
            print(f"  Dashboard '{name}' already exists (id={d['id']})")
            return d["id"]

    payload = {
        "dashboard_title": name,
        "slug": slug,
        "published": True,
    }
    r = requests.post(f"{BASE_URL}/api/v1/dashboard/", headers=h, json=payload)
    r.raise_for_status()
    dash_id = r.json()["id"]
    print(f"  Created dashboard '{name}' (id={dash_id})")
    return dash_id


def add_charts_to_dashboard(token, dashboard_id, chart_ids):
    """Update dashboard with chart layout using position_json."""
    h = headers(token)

    # Build a grid layout
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": ""}},
    }

    row_idx = 0
    col_per_row = 3
    chart_w = 4  # out of 12
    chart_h = 50

    for i, cid in enumerate(chart_ids):
        row = i // col_per_row
        col = i % col_per_row

        if col == 0:
            row_id = f"ROW-{row}"
            position[row_id] = {
                "type": "ROW", "id": row_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID"],
                "meta": {"background": "BACKGROUND_TRANSPARENT"}
            }
            position["GRID_ID"]["children"].append(row_id)

        chart_key = f"CHART-{cid}"
        row_id = f"ROW-{row}"
        position[row_id]["children"].append(chart_key)
        position[chart_key] = {
            "type": "CHART",
            "id": chart_key,
            "children": [],
            "parents": ["ROOT_ID", "GRID_ID", row_id],
            "meta": {
                "width": chart_w,
                "height": chart_h,
                "chartId": cid,
                "sliceName": f"chart_{cid}",
            }
        }

    payload = {
        "position_json": json.dumps(position),
    }
    r = requests.put(f"{BASE_URL}/api/v1/dashboard/{dashboard_id}", headers=h, json=payload)
    r.raise_for_status()
    print(f"  Updated dashboard {dashboard_id} with {len(chart_ids)} charts")


# ================================================================
# Main: Build all datasets, charts, and dashboards
# ================================================================
def main():
    print("=== Building Superset Dashboards ===\n")

    token = get_token()
    print("Got API token.\n")

    # --- Datasets ---
    print("Creating datasets...")
    ds_analyses = create_dataset(token, "analyses_review", "dev_gold")
    ds_restaurant = create_dataset(token, "dim_restaurant", "dev_silver")
    ds_user = create_dataset(token, "dim_user", "dev_silver")
    ds_review = create_dataset(token, "fact_review", "dev_silver")

    if not all([ds_analyses, ds_restaurant, ds_user, ds_review]):
        print("ERROR: Failed to create some datasets. Aborting.")
        sys.exit(1)

    print()

    # ================================================================
    # Dashboard 1: Restaurant Overview
    # ================================================================
    print("Building Dashboard 1: Restaurant Overview...")
    dash1 = create_dashboard(token, "Restaurant Overview", "restaurant-overview")
    charts1 = []

    charts1.append(create_chart(token, "Total Restaurants", ds_restaurant, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(DISTINCT restaurant_id)"},
        "header_font_size": 0.4,
        "subheader_font_size": 0.15,
    }, dashboards=[dash1]))

    charts1.append(create_chart(token, "Average Restaurant Rating", ds_restaurant, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "ROUND(AVG(stars), 2)"},
        "header_font_size": 0.4,
        "subheader_font_size": 0.15,
    }, dashboards=[dash1]))

    charts1.append(create_chart(token, "Total Reviews", ds_review, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(*)"},
        "header_font_size": 0.4,
        "subheader_font_size": 0.15,
    }, dashboards=[dash1]))

    charts1.append(create_chart(token, "Star Rating Distribution", ds_restaurant, "dist_bar", {
        "metrics": [{"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "count"}],
        "groupby": ["stars"],
        "order_desc": True,
        "color_scheme": "supersetColors",
        "show_legend": False,
        "x_axis_label": "Stars",
        "y_axis_label": "Count",
    }, dashboards=[dash1]))

    charts1.append(create_chart(token, "Top 20 Restaurants by Reviews", ds_restaurant, "dist_bar", {
        "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "review_count"}, "aggregate": "MAX", "label": "review_count"}],
        "groupby": ["restaurant_name"],
        "order_desc": True,
        "row_limit": 20,
        "color_scheme": "supersetColors",
        "x_axis_label": "Restaurant",
        "y_axis_label": "Reviews",
    }, dashboards=[dash1]))

    charts1.append(create_chart(token, "Open vs Closed Restaurants", ds_restaurant, "pie", {
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "count"},
        "groupby": ["is_open"],
        "color_scheme": "supersetColors",
        "show_labels": True,
        "label_type": "key_percent",
    }, dashboards=[dash1]))

    charts1 = [c for c in charts1 if c is not None]
    if charts1:
        add_charts_to_dashboard(token, dash1, charts1)
    print()

    # ================================================================
    # Dashboard 2: Review Analytics
    # ================================================================
    print("Building Dashboard 2: Review Analytics...")
    dash2 = create_dashboard(token, "Review Analytics", "review-analytics")
    charts2 = []

    charts2.append(create_chart(token, "Reviews Over Time", ds_analyses, "echarts_timeseries_line", {
        "metrics": [{"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "reviews"}],
        "x_axis": "review_date",
        "granularity_sqla": "review_date",
        "time_grain_sqla": "P1M",
        "color_scheme": "supersetColors",
        "show_legend": False,
    }, dashboards=[dash2]))

    charts2.append(create_chart(token, "Average Stars Over Time", ds_analyses, "echarts_timeseries_line", {
        "metrics": [{"expressionType": "SQL", "sqlExpression": "ROUND(AVG(stars), 2)", "label": "avg_stars"}],
        "x_axis": "review_date",
        "granularity_sqla": "review_date",
        "time_grain_sqla": "P1M",
        "color_scheme": "supersetColors",
    }, dashboards=[dash2]))

    charts2.append(create_chart(token, "Total Funny Votes", ds_analyses, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "SUM(funny)"},
        "header_font_size": 0.4,
    }, dashboards=[dash2]))

    charts2.append(create_chart(token, "Total Cool Votes", ds_analyses, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "SUM(cool)"},
        "header_font_size": 0.4,
    }, dashboards=[dash2]))

    charts2.append(create_chart(token, "Total Useful Votes", ds_analyses, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "SUM(useful)"},
        "header_font_size": 0.4,
    }, dashboards=[dash2]))

    charts2.append(create_chart(token, "Review Stars Distribution", ds_analyses, "dist_bar", {
        "metrics": [{"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "count"}],
        "groupby": ["stars"],
        "color_scheme": "supersetColors",
        "x_axis_label": "Stars",
        "y_axis_label": "Number of Reviews",
    }, dashboards=[dash2]))

    charts2 = [c for c in charts2 if c is not None]
    if charts2:
        add_charts_to_dashboard(token, dash2, charts2)
    print()

    # ================================================================
    # Dashboard 3: Geographic Analysis
    # ================================================================
    print("Building Dashboard 3: Geographic Analysis...")
    dash3 = create_dashboard(token, "Geographic Analysis", "geographic-analysis")
    charts3 = []

    charts3.append(create_chart(token, "Top 15 Cities by Restaurant Count", ds_restaurant, "dist_bar", {
        "metrics": [{"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "count"}],
        "groupby": ["city"],
        "order_desc": True,
        "row_limit": 15,
        "color_scheme": "supersetColors",
        "x_axis_label": "City",
        "y_axis_label": "Restaurants",
    }, dashboards=[dash3]))

    charts3.append(create_chart(token, "Restaurants by State", ds_restaurant, "treemap_v2", {
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "count"},
        "groupby": ["state"],
        "color_scheme": "supersetColors",
    }, dashboards=[dash3]))

    charts3.append(create_chart(token, "Average Rating by City", ds_analyses, "dist_bar", {
        "metrics": [{"expressionType": "SQL", "sqlExpression": "ROUND(AVG(restaurant_stars), 2)", "label": "avg_rating"}],
        "groupby": ["city"],
        "order_desc": True,
        "row_limit": 15,
        "color_scheme": "supersetColors",
        "x_axis_label": "City",
        "y_axis_label": "Avg Rating",
    }, dashboards=[dash3]))

    charts3.append(create_chart(token, "City Metrics", ds_analyses, "table", {
        "metrics": [
            {"expressionType": "SQL", "sqlExpression": "COUNT(DISTINCT restaurant_id)", "label": "restaurants"},
            {"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "reviews"},
            {"expressionType": "SQL", "sqlExpression": "ROUND(AVG(restaurant_stars), 2)", "label": "avg_rating"},
        ],
        "groupby": ["city", "state"],
        "order_desc": True,
        "row_limit": 50,
        "order_by_cols": ["[\"reviews\", false]"],
    }, dashboards=[dash3]))

    charts3 = [c for c in charts3 if c is not None]
    if charts3:
        add_charts_to_dashboard(token, dash3, charts3)
    print()

    # ================================================================
    # Dashboard 4: User Analytics
    # ================================================================
    print("Building Dashboard 4: User Analytics...")
    dash4 = create_dashboard(token, "User Analytics", "user-analytics")
    charts4 = []

    charts4.append(create_chart(token, "Total Users", ds_user, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(*)"},
        "header_font_size": 0.4,
    }, dashboards=[dash4]))

    charts4.append(create_chart(token, "Avg Reviews per User", ds_user, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "ROUND(AVG(review_count), 1)"},
        "header_font_size": 0.4,
    }, dashboards=[dash4]))

    charts4.append(create_chart(token, "Top 20 Most Active Reviewers", ds_user, "dist_bar", {
        "metrics": [{"expressionType": "SIMPLE", "column": {"column_name": "review_count"}, "aggregate": "MAX", "label": "reviews"}],
        "groupby": ["user_name"],
        "order_desc": True,
        "row_limit": 20,
        "color_scheme": "supersetColors",
    }, dashboards=[dash4]))

    charts4.append(create_chart(token, "User Rating Distribution", ds_user, "dist_bar", {
        "metrics": [{"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "users"}],
        "groupby": ["average_stars"],
        "color_scheme": "supersetColors",
        "x_axis_label": "Average Stars Given",
        "y_axis_label": "Users",
    }, dashboards=[dash4]))

    charts4 = [c for c in charts4 if c is not None]
    if charts4:
        add_charts_to_dashboard(token, dash4, charts4)
    print()

    # ================================================================
    # Dashboard 5: Executive Summary
    # ================================================================
    print("Building Dashboard 5: Executive Summary...")
    dash5 = create_dashboard(token, "Executive Summary", "executive-summary")
    charts5 = []

    charts5.append(create_chart(token, "KPI: Restaurants", ds_restaurant, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(DISTINCT restaurant_id)"},
        "subheader": "Total Restaurants",
        "header_font_size": 0.4,
    }, dashboards=[dash5]))

    charts5.append(create_chart(token, "KPI: Reviews", ds_review, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(*)"},
        "subheader": "Total Reviews",
        "header_font_size": 0.4,
    }, dashboards=[dash5]))

    charts5.append(create_chart(token, "KPI: Users", ds_user, "big_number_total", {
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(*)"},
        "subheader": "Total Users",
        "header_font_size": 0.4,
    }, dashboards=[dash5]))

    charts5.append(create_chart(token, "Top 5 Cities", ds_analyses, "pie", {
        "metric": {"expressionType": "SQL", "sqlExpression": "COUNT(DISTINCT restaurant_id)", "label": "restaurants"},
        "groupby": ["city"],
        "row_limit": 5,
        "color_scheme": "supersetColors",
        "show_labels": True,
        "label_type": "key_value",
    }, dashboards=[dash5]))

    charts5.append(create_chart(token, "Reviews Trend", ds_analyses, "echarts_timeseries_line", {
        "metrics": [{"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "reviews"}],
        "x_axis": "review_date",
        "granularity_sqla": "review_date",
        "time_grain_sqla": "P1M",
        "color_scheme": "supersetColors",
    }, dashboards=[dash5]))

    charts5.append(create_chart(token, "Top Categories", ds_analyses, "dist_bar", {
        "metrics": [{"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "count"}],
        "groupby": ["categories"],
        "order_desc": True,
        "row_limit": 10,
        "color_scheme": "supersetColors",
    }, dashboards=[dash5]))

    charts5 = [c for c in charts5 if c is not None]
    if charts5:
        add_charts_to_dashboard(token, dash5, charts5)
    print()

    print("=== Done! ===")
    print(f"Created 5 dashboards with charts.")
    print(f"Visit http://localhost:8088/dashboard/list/ to view them.")


if __name__ == "__main__":
    main()
