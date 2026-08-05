from datetime import date

import pandas as pd
import streamlit as st

from app.db import db_cursor, query_all, query_one
from app.utils.excel_export import export_document
from app.utils.ids import generate_doc_id
from streamlit_common.ui import confirm_delete_button

EMPTY_LINES = pd.DataFrame([{"ProductId": None, "Quantity": None}])


def _go(view, outbound_id=None):
    st.session_state["outbound_view"] = view
    st.session_state["outbound_selected_id"] = outbound_id
    st.rerun()


def _lines_editor(initial_df, products, editor_key):
    product_ids = [p["ProductId"] for p in products]
    return st.data_editor(
        initial_df,
        num_rows="dynamic",
        use_container_width=True,
        key=editor_key,
        column_config={
            "ProductId": st.column_config.SelectboxColumn("物料編號", options=product_ids, required=True),
            "Quantity": st.column_config.NumberColumn("數量", min_value=0, step=1, required=True),
        },
    )


def _parse_lines(edited_df):
    lines = []
    for record in edited_df.to_dict("records"):
        product_id = record.get("ProductId")
        qty = record.get("Quantity")
        if not product_id or qty in (None, ""):
            continue
        lines.append((product_id, qty))
    return lines


def _insert_lines(cur, outbound_id, lines):
    for line_num, (product_id, qty) in enumerate(lines, start=1):
        prod = query_one("SELECT ProductName FROM Product WHERE ProductId = ?", (product_id,))
        if not prod:
            raise ValueError(f"物料 {product_id} 不存在")
        cur.execute(
            "INSERT INTO OutboundDetail (OutboundId, LineNum, ProductId, ProductName, Quantity) VALUES (?, ?, ?, ?, ?)",
            (outbound_id, line_num, product_id, prod["ProductName"], qty),
        )


def _list_view():
    st.title("出庫管理")
    if st.button("+ 新增出庫單"):
        _go("new")

    rows = query_all(
        """
        SELECT h.OutboundId, h.OutboundDate, h.EmployeeId, e.EmployeeName,
               (SELECT COUNT(*) FROM OutboundDetail d WHERE d.OutboundId = h.OutboundId) AS LineCount
        FROM OutboundHeader h
        JOIN Employee e ON e.EmployeeId = h.EmployeeId
        ORDER BY h.OutboundId DESC
        """
    )
    if not rows:
        st.info("尚無出庫單")
        return

    for row in rows:
        col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 1, 2])
        col1.write(row["OutboundId"])
        col2.write(str(row["OutboundDate"]))
        col3.write(f"{row['EmployeeName']} ({row['EmployeeId']})")
        col4.write(f"{row['LineCount']} 筆")
        if col5.button("編輯", key=f"edit_{row['OutboundId']}"):
            _go("edit", row["OutboundId"])
        if confirm_delete_button(f"outbound_{row['OutboundId']}"):
            # 明細要先手動刪除、header 最後刪：理由同 inbound，見 CLAUDE.md「已知坑」。
            with db_cursor(commit=True) as cur:
                cur.execute("DELETE FROM OutboundDetail WHERE OutboundId = ?", (row["OutboundId"],))
                cur.execute("DELETE FROM OutboundHeader WHERE OutboundId = ?", (row["OutboundId"],))
            st.success(f"出庫單 {row['OutboundId']} 已刪除")
            st.rerun()


def _new_view():
    st.title("新增出庫單")
    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")
    employee_options = {f"{e['EmployeeId']} - {e['EmployeeName']}": e["EmployeeId"] for e in employees}

    outbound_date = st.date_input("日期", value=date.today())
    employee_label = st.selectbox("經手人", list(employee_options.keys())) if employee_options else None

    st.caption("明細")
    edited = _lines_editor(EMPTY_LINES, products, "outbound_new_lines_editor")

    col1, col2 = st.columns(2)
    save = col1.button("儲存", type="primary")
    if col2.button("取消"):
        _go("list")

    if save:
        lines = _parse_lines(edited)
        if not lines:
            st.error("至少要有一筆明細")
            return
        if not employee_label:
            st.error("請先建立員工資料")
            return
        employee_id = employee_options[employee_label]
        outbound_id = generate_doc_id("OutboundHeader", "OutboundId", "OUT", outbound_date)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO OutboundHeader (OutboundId, OutboundDate, EmployeeId) VALUES (?, ?, ?)",
                (outbound_id, outbound_date, employee_id),
            )
            _insert_lines(cur, outbound_id, lines)
        st.success(f"出庫單 {outbound_id} 新增成功")
        _go("list")


def _edit_view(outbound_id):
    header = query_one(
        """
        SELECT h.OutboundId, h.OutboundDate, h.EmployeeId, e.EmployeeName
        FROM OutboundHeader h JOIN Employee e ON e.EmployeeId = h.EmployeeId
        WHERE h.OutboundId = ?
        """,
        (outbound_id,),
    )
    if not header:
        st.error("找不到該出庫單")
        _go("list")
        return

    existing_lines = query_all(
        "SELECT LineNum, ProductId, ProductName, Quantity FROM OutboundDetail WHERE OutboundId = ? ORDER BY LineNum",
        (outbound_id,),
    )

    st.title(f"編輯出庫單 {outbound_id}")

    detail_columns = [("行號", "LineNum"), ("物料編號", "ProductId"), ("物料名稱", "ProductName"), ("數量", "Quantity")]
    header_fields = [
        ("單號", header["OutboundId"]),
        ("日期", str(header["OutboundDate"])),
        ("經手人", f"{header['EmployeeName']} ({header['EmployeeId']})"),
    ]
    buffer = export_document("出庫單", header_fields, detail_columns, existing_lines)
    st.download_button(
        "📥 匯出 Excel", data=buffer.getvalue(), file_name=f"{outbound_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")
    employee_options = {f"{e['EmployeeId']} - {e['EmployeeName']}": e["EmployeeId"] for e in employees}
    current_label = next(
        (label for label, eid in employee_options.items() if eid == header["EmployeeId"]), None
    )

    outbound_date = st.date_input("日期", value=header["OutboundDate"])
    employee_label = st.selectbox(
        "經手人", list(employee_options.keys()),
        index=list(employee_options.keys()).index(current_label) if current_label else 0,
    )

    st.caption("明細")
    lines_df = pd.DataFrame(
        [{"ProductId": r["ProductId"], "Quantity": r["Quantity"]} for r in existing_lines]
    ) if existing_lines else EMPTY_LINES
    edited = _lines_editor(lines_df, products, f"outbound_edit_lines_{outbound_id}")

    col1, col2 = st.columns(2)
    save = col1.button("儲存", type="primary")
    if col2.button("回列表"):
        _go("list")

    if save:
        lines = _parse_lines(edited)
        if not lines:
            st.error("至少要有一筆明細")
            return
        employee_id = employee_options[employee_label]
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE OutboundHeader SET OutboundDate = ?, EmployeeId = ? WHERE OutboundId = ?",
                (outbound_date, employee_id, outbound_id),
            )
            cur.execute("DELETE FROM OutboundDetail WHERE OutboundId = ?", (outbound_id,))
            _insert_lines(cur, outbound_id, lines)
        st.success("更新成功")
        _go("list")


def render():
    view = st.session_state.get("outbound_view", "list")
    selected_id = st.session_state.get("outbound_selected_id")

    if view == "new":
        _new_view()
    elif view == "edit" and selected_id:
        _edit_view(selected_id)
    else:
        _list_view()
