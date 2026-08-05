import pymssql
import streamlit as st

from streamlit_common.db import execute, query_all, query_one
from streamlit_common.ui import confirm_delete_button


def _go(view, product_id=None):
    st.session_state["product_view"] = view
    st.session_state["product_selected_id"] = product_id
    st.rerun()


def _list_view():
    st.title("物料管理")
    if st.button("+ 新增物料"):
        _go("new")

    rows = query_all("SELECT ProductId, ProductName, StockBalance FROM Product ORDER BY ProductId")
    if not rows:
        st.info("尚無物料資料")
        return

    for row in rows:
        col1, col2, col3, col4 = st.columns([2, 4, 2, 2])
        col1.write(row["ProductId"])
        col2.write(row["ProductName"])
        col3.write(row["StockBalance"])
        if col4.button("查看", key=f"view_{row['ProductId']}"):
            _go("detail", row["ProductId"])


def _new_view():
    st.title("新增物料")
    with st.form("product_new_form"):
        product_id = st.text_input("物料編號", max_chars=20)
        name = st.text_input("物料名稱", max_chars=100)
        stock = st.number_input("庫存量", step=0.001, value=0.0)
        submitted = st.form_submit_button("儲存")
    if st.button("取消"):
        _go("list")

    if submitted:
        product_id = product_id.strip()
        name = name.strip()
        if not product_id or not name:
            st.error("物料編號與名稱為必填")
            return
        try:
            execute(
                "INSERT INTO Product (ProductId, ProductName, StockBalance) VALUES (?, ?, ?)",
                (product_id, name, stock),
            )
        except pymssql.IntegrityError:
            st.error(f"物料編號 {product_id} 已存在")
            return
        st.success("新增成功")
        _go("list")


def _edit_view(product_id):
    row = query_one("SELECT * FROM Product WHERE ProductId = ?", (product_id,))
    if not row:
        st.error("找不到該物料")
        _go("list")
        return

    st.title(f"編輯物料 {product_id}")
    with st.form("product_edit_form"):
        st.text_input("物料編號", value=product_id, disabled=True)
        name = st.text_input("物料名稱", value=row["ProductName"], max_chars=100)
        stock = st.number_input("庫存量", step=0.001, value=float(row["StockBalance"] or 0))
        submitted = st.form_submit_button("儲存")
    if st.button("取消"):
        _go("detail", product_id)

    if submitted:
        name = name.strip()
        if not name:
            st.error("名稱為必填")
            return
        execute(
            "UPDATE Product SET ProductName = ?, StockBalance = ? WHERE ProductId = ?",
            (name, stock, product_id),
        )
        st.success("更新成功")
        _go("detail", product_id)


def _detail_view(product_id):
    row = query_one("SELECT * FROM Product WHERE ProductId = ?", (product_id,))
    if not row:
        st.error("找不到該物料")
        _go("list")
        return

    st.title(f"物料 {product_id}")
    st.write(f"**物料名稱**：{row['ProductName']}")
    st.write(f"**庫存量**：{row['StockBalance']}")

    col1, col2, col3 = st.columns([1, 1, 4])
    if col1.button("編輯"):
        _go("edit", product_id)
    if col2.button("回列表"):
        _go("list")

    st.subheader("入出明細")
    details = query_all(
        "SELECT DocType, DocId, LineNum, Quantity FROM v_InoutDetail WHERE ProductId = ? ORDER BY DocId, LineNum",
        (product_id,),
    )
    if details:
        st.dataframe(details, hide_index=True, use_container_width=True)
    else:
        st.caption("尚無入出明細")

    st.divider()
    count = query_one("SELECT COUNT(*) AS c FROM v_InoutDetail WHERE ProductId = ?", (product_id,))["c"]
    if count > 0:
        st.caption(f"此物料已有 {count} 筆入出明細，無法刪除")
    elif confirm_delete_button(f"product_{product_id}"):
        try:
            execute("DELETE FROM Product WHERE ProductId = ?", (product_id,))
            st.success("刪除成功")
            _go("list")
        except pymssql.IntegrityError:
            st.error("此物料仍被其他資料參照，無法刪除")


def render():
    view = st.session_state.get("product_view", "list")
    selected_id = st.session_state.get("product_selected_id")

    if view == "new":
        _new_view()
    elif view == "edit" and selected_id:
        _edit_view(selected_id)
    elif view == "detail" and selected_id:
        _detail_view(selected_id)
    else:
        _list_view()
