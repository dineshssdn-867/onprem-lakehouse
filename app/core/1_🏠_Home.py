import streamlit as st
from core.auth.authenticator import Auth

st.set_page_config(page_title="Recommendation System", page_icon=":bar_chart:", layout="wide")


class HomePage:
    def __init__(self):
        self._authenticator = Auth()

    def _show_home_page(self):
        st.title('Restaurant Recommender')
        st.write(f'Welcome, **{st.session_state.get("username", "Guest")}**!')
        st.write('Navigate to the **Recommender** page in the sidebar to get started.')

        if st.button("Logout"):
            self._authenticator.logout()
            st.rerun()

    def show(self):
        self._show_home_page()

    def main(self):
        hide_bar = """
            <style>
            [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
                visibility:hidden;
                width: 0px;
            }
            [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
                visibility:hidden;
            }
            </style>
        """

        authentication_status = self._authenticator.login()

        if authentication_status:
            self.show()

        elif authentication_status is False:
            st.error('Username/password is incorrect')
            st.markdown(hide_bar, unsafe_allow_html=True)

        elif authentication_status is None:
            st.warning('Please enter your username and password')
            st.markdown(hide_bar, unsafe_allow_html=True)


if __name__ == '__main__':
    home = HomePage()
    home.main()
