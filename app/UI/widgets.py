import streamlit as st
from script.utils import fetch_poster
from PIL import Image

from constants import DEFAULT_RES_NUMBER


def initialize_res_widget(cfg, st_module, res_number=DEFAULT_RES_NUMBER):
    """Create empty column placeholders for recommended restaurants."""
    st_module.button(cfg["title"])
    res_cols = st_module.columns(res_number)
    for c in res_cols:
        with c:
            st_module.empty()
    return res_cols


def detail_item(business_id, selected_rows, st_module):
    image = fetch_poster(business_id)
    detail = open("assets/detail.html", 'r', encoding='utf-8').read()
    detail = detail.replace("{{ img }}", image)
    detail = detail.replace("{{ name }}", selected_rows.iloc[0]['name'])
    detail = detail.replace("{{ categories }}", selected_rows.iloc[0]['categories'])
    detail = detail.replace("{{ add }}", selected_rows.iloc[0]['address'])
    detail = detail.replace("{{ score }}", str(round(selected_rows.iloc[0]['score'], 2)))
    is_open = "Opening" if selected_rows.iloc[0]['is_open'] == 1 else 'Closed'
    detail = detail.replace("{{ is_open }}", is_open)
    st_module.markdown(detail, unsafe_allow_html=True)


def show_recommended_res_info(recommended_res, res_cols, show_score, st_module, section="default"):
    """Display recommended restaurants with images and optional scores."""
    if recommended_res.empty:
        return

    res_ids = recommended_res["business_id"]
    res_name = recommended_res["name"]
    res_scores = recommended_res["score"]
    posters = [fetch_poster(i) for i in res_ids]

    for index, (c, name, score, img) in enumerate(zip(res_cols, res_name, res_scores, posters)):
        with c:
            if st.button(name, key=f"btn_{section}_{index}"):
                st.session_state["selected_restaurant"] = name
            st.markdown("""<style>.element-container.css-1047zxe.e1tzin5v3 .row-widget.stButton>* {
                                padding: 0;
                                border: 0;
                                margin: 0;
                                color: white;
                                background-color: transparent;
                        }
                        </style>
                        """, unsafe_allow_html=True)
            try:
                img = Image.open(img)
            except Exception:
                pass
            st.image(img)
            if show_score:
                st.write(round(score, 3))
