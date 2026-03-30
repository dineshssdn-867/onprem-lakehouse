import pandas as pd
import streamlit as st

from script.api import request_recommend
from script.connect import Connect


def make_card_element(userid, res_number):
    try:
        recommended_res = request_recommend({
            "userid": userid,
            "res_num": res_number,
            "token": "systemapi"
        })

        if not isinstance(recommended_res, dict) or "results" not in recommended_res:
            st.warning("Personalized recommendations unavailable (model may not be trained).")
            return pd.DataFrame(columns=["business_id", "name", "score"])

        conn = Connect()
        results = {"business_id": [], "name": [], "score": []}

        for res in recommended_res["results"]:
            bid = res.get('businessid')
            businessid = conn.get_fetchone(
                "SELECT DISTINCT(business_id) FROM bronze.restaurant_transform WHERE businessid = ?",
                (bid,)
            )
            name = conn.get_fetchone(
                "SELECT DISTINCT(name) FROM bronze.restaurant_transform WHERE businessid = ?",
                (bid,)
            )
            if businessid and name:
                results["business_id"].append(businessid)
                results["name"].append(name)
                results["score"].append(res.get("rating", 0))

        conn.close()
        return pd.DataFrame.from_dict(results)

    except Exception as e:
        st.warning(f"Personalized recommendations unavailable: {e}")
        return pd.DataFrame(columns=["business_id", "name", "score"])
