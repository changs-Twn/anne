import streamlit as st

from app.blueprints.employee import DEFAULT_PASSWORD, PASSWORD_RE
from app.db import execute, query_one

SUPER_ID = "Super"
SUPER_PASSWORD = "Super"


def require_login():
    """Render a login form and st.stop() until logged in.

    Mirrors app/__init__.py's before_request hook + app/blueprints/auth.py's login().
    """
    if st.session_state.get("employee_id"):
        return

    st.title("Mini ERP 登入")
    with st.form("login_form"):
        employee_id = st.text_input("員工編號")
        password = st.text_input("密碼", type="password")
        submitted = st.form_submit_button("登入")

    if submitted:
        employee_id = employee_id.strip()
        password = password.strip()

        if employee_id == SUPER_ID and password == SUPER_PASSWORD:
            st.session_state["employee_id"] = SUPER_ID
            st.session_state["employee_name"] = "Super"
            st.session_state["is_super"] = True
            st.rerun()

        row = query_one(
            "SELECT EmployeeId, EmployeeName, Password FROM Employee WHERE EmployeeId = ?",
            (employee_id,),
        )
        if row and row["Password"].strip() == password:
            st.session_state["employee_id"] = row["EmployeeId"]
            st.session_state["employee_name"] = row["EmployeeName"]
            st.session_state["is_super"] = False
            # 密碼還是預設值 → 視為第一次登入，提示（可跳過）改密碼一次
            st.session_state["prompt_password_change"] = password == DEFAULT_PASSWORD
            st.rerun()
        else:
            st.error("員工編號或密碼錯誤")

    st.stop()


def render_password_prompt():
    """One-shot "please change your default password" prompt, popped after first render."""
    if not st.session_state.pop("prompt_password_change", False):
        return

    with st.expander("請更新您的密碼（目前使用預設密碼 123456）", expanded=True):
        with st.form("password_change_form"):
            new_password = st.text_input("新密碼", type="password", max_chars=6)
            confirm_password = st.text_input("確認新密碼", type="password", max_chars=6)
            col1, col2 = st.columns(2)
            update = col1.form_submit_button("更新密碼")
            col2.form_submit_button("稍後再說")

        if update:
            new_password = new_password.strip()
            confirm_password = confirm_password.strip()
            if new_password != confirm_password:
                st.error("兩次輸入的密碼不一致")
            elif not PASSWORD_RE.match(new_password):
                st.error("密碼必須是 6 碼英數字")
            else:
                execute(
                    "UPDATE Employee SET Password = ? WHERE EmployeeId = ?",
                    (new_password, st.session_state["employee_id"]),
                )
                st.success("密碼已更新")


def render_sidebar_user():
    name = st.session_state.get("employee_name", "")
    suffix = "（Super）" if st.session_state.get("is_super") else ""
    st.sidebar.markdown(f"**{name}{suffix}**")
    if st.sidebar.button("登出"):
        st.session_state.clear()
        st.rerun()
