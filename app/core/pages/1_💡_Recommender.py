import pickle

import streamlit as st

from script.make import make_card_element
from script.recommender import contend_based_recommendations, weighted_average_based_recommendations, read_item
from UI.widgets import initialize_res_widget, show_recommended_res_info, detail_item
from constants import DEFAULT_RES_NUMBER
from config import line1, line2, line3

st.set_page_config(page_title="Recommender system", layout="wide")

# Styling
with open('./assets/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load data
with open('data/res_df.pickle', 'rb') as handle:
    res = pickle.load(handle)

with open('data/res_scores.pickle', 'rb') as handle:
    fullRes = pickle.load(handle)

# Title
title = '<p style="font-family:Courier; color:White; font-size: 50px;"><b>Restaurant Recommender system</b></p>'
st.markdown(title, unsafe_allow_html=True)

# Sidebar controls
res_number = st.sidebar.slider("Recommended restaurant number", min_value=5, max_value=10, value=DEFAULT_RES_NUMBER)
show_score = st.sidebar.checkbox("Show score")

# Initialize session state
if "selected_restaurant" not in st.session_state:
    st.session_state["selected_restaurant"] = None

selected = st.session_state.get("selected_restaurant")

if selected is not None:
    # ── Detail View ──
    if st.button("← Back to recommendations"):
        st.session_state["selected_restaurant"] = None
        st.rerun()

    if selected in fullRes["name"].values:
        business_id, selected_rows = read_item(selected, fullRes)
        detail_item(business_id, selected_rows, st)

        # Related restaurants (content-based)
        col_for_content_based = initialize_res_widget(line2, st, res_number)
        related = contend_based_recommendations(res, [selected_rows.iloc[0]['name']], res_number)
        show_recommended_res_info(related, col_for_content_based, show_score, st, section="related")
    else:
        st.warning("Restaurant not found in the scored dataset.")
        st.session_state["selected_restaurant"] = None

else:
    # ── Main View ──

    # Search bar
    main_layout, search_layout = st.columns([10, 1])
    options = main_layout.multiselect('Which restaurant do you like?', res["name"].unique())
    show_recommended_res_btn = search_layout.button("search")

    # Score-based recommendations (same for all users)
    col_for_score_based = initialize_res_widget(line1, st, res_number)
    score_based = weighted_average_based_recommendations(fullRes, res_number)
    show_recommended_res_info(score_based, col_for_score_based, show_score, st, section="score")

    # ALS personalized recommendations
    userid = st.session_state.get("userid")
    if userid is not None:
        col_for_user = initialize_res_widget(line3, st, res_number)
        als_recommend = make_card_element(userid, res_number)
        if not als_recommend.empty:
            show_recommended_res_info(als_recommend, col_for_user, show_score, st, section="als")

    # Content-based search results
    if show_recommended_res_btn and options:
        col_for_search = initialize_res_widget(line2, st, res_number)
        search_results = contend_based_recommendations(res, options, res_number)
        show_recommended_res_info(search_results, col_for_search, show_score, st, section="search")
