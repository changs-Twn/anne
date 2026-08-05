from datetime import date

import pandas as pd
import streamlit as st

from app.utils.excel_export import export_document
from streamlit_common.db import db_cursor, generate_doc_id, query_all, query_one
from streamlit_common.ui import confirm_delete_button

EMPTY_LINES = pd.DataFrame([{"ProductId": None, "Quantity": None}])


def _go(view, inbound_id=None):
    st.session_state["inbound_view"] = view
    st.session_state["inbound_selected_id"] = inbound_id
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


def _insert_lines(cur, inbound_id, lines):
    for line_num, (product_id, qty) in enumerate(lines, start=1):
        prod = query_one("SELECT ProductName FROM Product WHERE ProductId = ?", (product_id,))
        if not prod:
            raise ValueError(f"物料 {product_id} 不存在")
        cur.execute(
            "INSERT INTO InboundDetail (InboundId, LineNum, ProductId, ProductName, Quantity) VALUES (?, ?, ?, ?, ?)",
            (inbound_id, line_num, product_id, prod["ProductName"], qty),
        )


def _list_view():
    st.title("入庫管理")
    if st.button("+ 新增入庫單"):
        _go("new")

    rows = query_all(
        """
        SELECT h.InboundId, h.InboundDate, h.EmployeeId, e.EmployeeName,
               (SELECT COUNT(*) FROM InboundDetail d WHERE d.InboundId = h.InboundId) AS LineCount
        FROM InboundHeader h
        JOIN Employee e ON e.EmployeeId = h.EmployeeId
        ORDER BY h.InboundId DESC
        """
    )
    if not rows:
        st.info("尚無入庫單")
        return

    for row in rows:
        col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 1, 2])
        col1.write(row["InboundId"])
        col2.write(str(row["InboundDate"]))
        col3.write(f"{row['EmployeeName']} ({row['EmployeeId']})")
        col4.write(f"{row['LineCount']} 筆")
        if col5.button("編輯", key=f"edit_{row['InboundId']}"):
            _go("edit", row["InboundId"])
        if confirm_delete_button(f"inbound_{row['InboundId']}"):
            # 明細要先手動刪除、header 最後刪：DB 的 trg_InboundDetail_DailyClosing 在算日結餘額 delta
            # 時會 JOIN InboundHeader 取日期，若靠 FK CASCADE 讓 header 先被刪掉，明細的 AFTER DELETE
            # trigger 觸發時 header 已經不存在，JOIN 會是空集合，日結餘額表就不會被回沖
            # （驗證過的真實案例，見 CLAUDE.md「已知坑」）。
            with db_cursor(commit=True) as cur:
                cur.execute("DELETE FROM InboundDetail WHERE InboundId = ?", (row["InboundId"],))
                cur.execute("DELETE FROM InboundHeader WHERE InboundId = ?", (row["InboundId"],))
            st.success(f"入庫單 {row['InboundId']} 已刪除")
            st.rerun()


def _new_view():
    st.title("新增入庫單")
    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")
    employee_options = {f"{e['EmployeeId']} - {e['EmployeeName']}": e["EmployeeId"] for e in employees}

    inbound_date = st.date_input("日期", value=date.today())
    employee_label = st.selectbox("經手人", list(employee_options.keys())) if employee_options else None

    st.caption("明細")
    edited = _lines_editor(EMPTY_LINES, products, "inbound_new_lines_editor")

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
        inbound_id = generate_doc_id("InboundHeader", "InboundId", "IN", inbound_date)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO InboundHeader (InboundId, InboundDate, EmployeeId) VALUES (?, ?, ?)",
                (inbound_id, inbound_date, employee_id),
            )
            _insert_lines(cur, inbound_id, lines)
        st.success(f"入庫單 {inbound_id} 新增成功")
        _go("list")


def _edit_view(inbound_id):
    header = query_one(
        """
        SELECT h.InboundId, h.InboundDate, h.EmployeeId, e.EmployeeName
        FROM InboundHeader h JOIN Employee e ON e.EmployeeId = h.EmployeeId
        WHERE h.InboundId = ?
        """,
        (inbound_id,),
    )
    if not header:
        st.error("找不到該入庫單")
        _go("list")
        return

    existing_lines = query_all(
        "SELECT LineNum, ProductId, ProductName, Quantity FROM InboundDetail WHERE InboundId = ? ORDER BY LineNum",
        (inbound_id,),
    )

    st.title(f"編輯入庫單 {inbound_id}")

    detail_columns = [("行號", "LineNum"), ("物料編號", "ProductId"), ("物料名稱", "ProductName"), ("數量", "Quantity")]
    header_fields = [
        ("單號", header["InboundId"]),
        ("日期", str(header["InboundDate"])),
        ("經手人", f"{header['EmployeeName']} ({header['EmployeeId']})"),
    ]
    buffer = export_document("入庫單", header_fields, detail_columns, existing_lines)
    st.download_button(
        "📥 匯出 Excel", data=buffer.getvalue(), file_name=f"{inbound_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")
    employee_options = {f"{e['EmployeeId']} - {e['EmployeeName']}": e["EmployeeId"] for e in employees}
    current_label = next(
        (label for label, eid in employee_options.items() if eid == header["EmployeeId"]), None
    )

    inbound_date = st.date_input("日期", value=header["InboundDate"])
    employee_label = st.selectbox(
        "經手人", list(employee_options.keys()),
        index=list(employee_options.keys()).index(current_label) if current_label else 0,
    )

    st.caption("明細")
    lines_df = pd.DataFrame(
        [{"ProductId": r["ProductId"], "Quantity": r["Quantity"]} for r in existing_lines]
    ) if existing_lines else EMPTY_LINES
    edited = _lines_editor(lines_df, products, f"inbound_edit_lines_{inbound_id}")

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
                "UPDATE InboundHeader SET InboundDate = ?, EmployeeId = ? WHERE InboundId = ?",
                (inbound_date, employee_id, inbound_id),
            )
            cur.execute("DELETE FROM InboundDetail WHERE InboundId = ?", (inbound_id,))
            _insert_lines(cur, inbound_id, lines)
        st.success("更新成功")
        _go("list")


def render():
    view = st.session_state.get("inbound_view", "list")
    selected_id = st.session_state.get("inbound_selected_id")

    if view == "new":
        _new_view()
    elif view == "edit" and selected_id:
        _edit_view(selected_id)
    else:
        _list_view()
