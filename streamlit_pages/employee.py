import pyodbc
import streamlit as st

from app.blueprints.employee import DEFAULT_PASSWORD, PASSWORD_RE
from app.db import execute, query_all, query_one
from streamlit_common.ui import confirm_delete_button


def _can_access(employee_id):
    """Super 可以存取任何員工紀錄；一般使用者只能存取自己的。"""
    return st.session_state.get("is_super") or st.session_state.get("employee_id") == employee_id


def _go(view, employee_id=None):
    st.session_state["employee_view"] = view
    st.session_state["employee_selected_id"] = employee_id
    st.rerun()


def _list_view():
    st.title("員工管理")
    if st.session_state.get("is_super") and st.button("+ 新增員工"):
        _go("new")

    rows = query_all("SELECT EmployeeId, EmployeeName, Email FROM Employee ORDER BY EmployeeId")
    if not rows:
        st.info("尚無員工資料")
        return

    for row in rows:
        col1, col2, col3, col4 = st.columns([2, 3, 3, 2])
        col1.write(row["EmployeeId"])
        col2.write(row["EmployeeName"])
        col3.write(row["Email"] or "")
        if _can_access(row["EmployeeId"]):
            if col4.button("查看", key=f"view_{row['EmployeeId']}"):
                _go("detail", row["EmployeeId"])
        else:
            col4.write("—")


def _new_view():
    if not st.session_state.get("is_super"):
        st.error("只有 Super 可以新增員工")
        _go("list")
        return

    st.title("新增員工")
    with st.form("employee_new_form"):
        employee_id = st.text_input("員工編號", max_chars=20)
        name = st.text_input("姓名", max_chars=50)
        email = st.text_input("Email", max_chars=255)
        password = st.text_input(
            "密碼", value=DEFAULT_PASSWORD, max_chars=6,
            help="6 碼英數字，新增時預設 123456。",
        )
        submitted = st.form_submit_button("儲存")
    if st.button("取消"):
        _go("list")

    if submitted:
        employee_id = employee_id.strip()
        name = name.strip()
        email = email.strip() or None
        password = password.strip() or DEFAULT_PASSWORD
        if not employee_id or not name:
            st.error("員工編號與姓名為必填")
            return
        if not PASSWORD_RE.match(password):
            st.error("密碼必須是 6 碼英數字")
            return
        try:
            execute(
                "INSERT INTO Employee (EmployeeId, EmployeeName, Email, Password) VALUES (?, ?, ?, ?)",
                (employee_id, name, email, password),
            )
        except pyodbc.IntegrityError:
            st.error(f"員工編號 {employee_id} 已存在")
            return
        st.success("新增成功")
        _go("list")


def _edit_view(employee_id):
    if not _can_access(employee_id):
        st.error("您沒有權限編輯其他員工的資料")
        _go("list")
        return

    row = query_one("SELECT * FROM Employee WHERE EmployeeId = ?", (employee_id,))
    if not row:
        st.error("找不到該員工")
        _go("list")
        return

    st.title(f"編輯員工 {employee_id}")
    with st.form("employee_edit_form"):
        st.text_input("員工編號", value=employee_id, disabled=True)
        name = st.text_input("姓名", value=row["EmployeeName"], max_chars=50)
        email = st.text_input("Email", value=row["Email"] or "", max_chars=255)
        password = st.text_input(
            "密碼", value=row["Password"].strip(), max_chars=6,
            help="6 碼英數字，新增時預設 123456。",
        )
        submitted = st.form_submit_button("儲存")
    if st.button("取消"):
        _go("detail", employee_id)

    if submitted:
        name = name.strip()
        email = email.strip() or None
        password = password.strip()
        if not name:
            st.error("姓名為必填")
            return
        if not PASSWORD_RE.match(password):
            st.error("密碼必須是 6 碼英數字")
            return
        execute(
            "UPDATE Employee SET EmployeeName = ?, Email = ?, Password = ? WHERE EmployeeId = ?",
            (name, email, password, employee_id),
        )
        st.success("更新成功")
        _go("detail", employee_id)


def _detail_view(employee_id):
    if not _can_access(employee_id):
        st.error("您沒有權限查看其他員工的資料")
        _go("list")
        return

    row = query_one("SELECT * FROM Employee WHERE EmployeeId = ?", (employee_id,))
    if not row:
        st.error("找不到該員工")
        _go("list")
        return

    st.title(f"員工 {employee_id}")
    st.write(f"**姓名**：{row['EmployeeName']}")
    st.write(f"**Email**：{row['Email'] or ''}")

    col1, col2, col3 = st.columns([1, 1, 4])
    if col1.button("編輯"):
        _go("edit", employee_id)
    if col2.button("回列表"):
        _go("list")

    st.subheader("入出單據")
    details = query_all(
        "SELECT DocType, DocId, DocDate FROM v_InoutHeader WHERE EmployeeId = ? ORDER BY DocDate DESC, DocId",
        (employee_id,),
    )
    if details:
        st.dataframe(details, hide_index=True, use_container_width=True)
    else:
        st.caption("尚無入出單據")

    st.divider()
    count = query_one("SELECT COUNT(*) AS c FROM v_InoutHeader WHERE EmployeeId = ?", (employee_id,))["c"]
    if count > 0:
        st.caption(f"此員工已有 {count} 筆入出單據，無法刪除")
    elif confirm_delete_button(f"employee_{employee_id}"):
        try:
            execute("DELETE FROM Employee WHERE EmployeeId = ?", (employee_id,))
            st.success("刪除成功")
            # 刪的是自己的帳號：帳號已經不存在了，直接登出
            if st.session_state.get("employee_id") == employee_id:
                st.session_state.clear()
                st.rerun()
            _go("list")
        except pyodbc.IntegrityError:
            st.error("此員工仍被其他資料參照，無法刪除")


def render():
    view = st.session_state.get("employee_view", "list")
    selected_id = st.session_state.get("employee_selected_id")

    if view == "new":
        _new_view()
    elif view == "edit" and selected_id:
        _edit_view(selected_id)
    elif view == "detail" and selected_id:
        _detail_view(selected_id)
    else:
        _list_view()
