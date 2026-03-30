"""Fix dashboard layouts with correct Superset position_json format."""
import requests
import json

BASE_URL = "http://localhost:8088"

def get_token():
    r = requests.post(f"{BASE_URL}/api/v1/security/login", json={
        "username": "admin", "password": "admin123",
        "provider": "db", "refresh": True
    })
    return r.json()["access_token"]

def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def build_position_json(chart_ids, chart_names):
    """Build correct Superset v2 position_json."""
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": ""}},
    }

    cols_per_row = 3
    col_width = 4  # each col out of 12

    for i, (cid, cname) in enumerate(zip(chart_ids, chart_names)):
        row_num = i // cols_per_row
        col_num = i % cols_per_row
        row_id = f"ROW-row-{row_num}"

        # Create row if first column
        if col_num == 0:
            position[row_id] = {
                "type": "ROW",
                "id": row_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID"],
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
            }
            position["GRID_ID"]["children"].append(row_id)

        # Create chart container
        chart_id_str = f"CHART-explore-{cid}-1"
        position[row_id]["children"].append(chart_id_str)
        position[chart_id_str] = {
            "type": "CHART",
            "id": chart_id_str,
            "children": [],
            "parents": ["ROOT_ID", "GRID_ID", row_id],
            "meta": {
                "width": col_width,
                "height": 50,
                "chartId": cid,
                "sliceName": cname,
                "uuid": f"chart-{cid}",
            },
        }

    return position


def update_dashboard(token, dash_id, chart_ids, chart_names):
    h = headers(token)
    position = build_position_json(chart_ids, chart_names)

    # Build json_metadata with chart filter scopes
    json_metadata = {
        "timed_refresh_immune_slices": [],
        "expanded_slices": {},
        "refresh_frequency": 0,
        "default_filters": "{}",
        "color_scheme": "supersetColors",
        "label_colors": {},
        "shared_label_colors": {},
        "color_scheme_domain": [],
        "cross_filters_enabled": True,
    }

    payload = {
        "position_json": json.dumps(position),
        "json_metadata": json.dumps(json_metadata),
    }
    r = requests.put(f"{BASE_URL}/api/v1/dashboard/{dash_id}", headers=h, json=payload)
    r.raise_for_status()
    print(f"  Fixed dashboard {dash_id} with {len(chart_ids)} charts")


def main():
    token = get_token()
    print("Fixing dashboard layouts...\n")

    # Dashboard 1: Restaurant Overview (charts 1-6)
    update_dashboard(token, 1,
        [1, 2, 3, 4, 5, 6],
        ["Total Restaurants", "Average Restaurant Rating", "Total Reviews",
         "Star Rating Distribution", "Top 20 Restaurants by Reviews", "Open vs Closed Restaurants"])

    # Dashboard 2: Review Analytics (charts 7-12)
    update_dashboard(token, 2,
        [7, 8, 9, 10, 11, 12],
        ["Reviews Over Time", "Average Stars Over Time", "Total Funny Votes",
         "Total Cool Votes", "Total Useful Votes", "Review Stars Distribution"])

    # Dashboard 3: Geographic Analysis (charts 13-16)
    update_dashboard(token, 3,
        [13, 14, 15, 16],
        ["Top 15 Cities by Restaurant Count", "Restaurants by State",
         "Average Rating by City", "City Metrics"])

    # Dashboard 4: User Analytics (charts 17-20)
    update_dashboard(token, 4,
        [17, 18, 19, 20],
        ["Total Users", "Avg Reviews per User",
         "Top 20 Most Active Reviewers", "User Rating Distribution"])

    # Dashboard 5: Executive Summary (charts 21-26)
    update_dashboard(token, 5,
        [21, 22, 23, 24, 25, 26],
        ["KPI: Restaurants", "KPI: Reviews", "KPI: Users",
         "Top 5 Cities", "Reviews Trend", "Top Categories"])

    print("\nDone! Refresh the dashboards in your browser.")


if __name__ == "__main__":
    main()
