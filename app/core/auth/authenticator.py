import os

from trino.dbapi import connect
import streamlit as st


class Auth:
    def __init__(self):
        self._db_connection = self._connect_db()

    def _get_user_name(self, account_name: str):
        cursor = self._db_connection.cursor()
        cursor.execute(
            "SELECT DISTINCT(account_name) FROM bronze.user_account WHERE account_name = ?",
            (account_name,)
        )
        result = cursor.fetchone()
        cursor.close()
        if result is not None:
            return result[0]
        return None

    def _get_user_password(self, account_name: str):
        cursor = self._db_connection.cursor()
        cursor.execute(
            "SELECT DISTINCT(account_pass) FROM bronze.user_account WHERE account_name = ?",
            (account_name,)
        )
        result = cursor.fetchone()
        cursor.close()
        if result is not None:
            return result[0]
        return None

    def _get_user_id(self, account_name: str):
        cursor = self._db_connection.cursor()
        cursor.execute(
            "SELECT DISTINCT(userid) FROM bronze.user_account WHERE account_name = ?",
            (account_name,)
        )
        result = cursor.fetchone()
        cursor.close()
        if result is not None:
            return result[0]
        return None

    def _connect_db(self):
        host = os.environ.get("TRINO_HOST", "trino")
        port = int(os.environ.get("TRINO_PORT", "8080"))
        conn = connect(host=host, port=port, user="trino", catalog="lakehouse")
        return conn

    def login(self):
        # Already logged in — preserve session across page navigation
        if st.session_state.get('username') is not None:
            return True

        placeholder = st.empty()
        with placeholder.form("login", clear_on_submit=True):
            st.markdown("#### Enter your credentials")
            user = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

        if not submit:
            return None

        username = self._get_user_name(user)
        stored_password = self._get_user_password(user) if username else None

        if user == username and password == stored_password:
            placeholder.empty()
            st.session_state['username'] = username
            st.session_state['userid'] = self._get_user_id(user)
            return True
        else:
            st.error("Login failed")
            return False

    def logout(self):
        for key in ['username', 'userid', 'selected_restaurant']:
            if key in st.session_state:
                del st.session_state[key]
