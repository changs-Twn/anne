import streamlit as st

from app.utils.excel_export import export_report
from streamlit_common.db import query_all

# Mirrors app/blueprints/reports.py's filter builders / query runners exactly,
# but sourced from streamlit_common.db (pymssql) instead of app.db (pyodbc) —
# see streamlit_common/db.py for why the Streamlit app can't share app.db.


def _header_filter(args):
    where = ["1=1"]
    params = []
    if args.get("date_from"):
        where.append("h.DocDate >= ?")
        params.append(args["date_from"])
    if args.get("date_to"):
        where.append("h.DocDate <= ?")
        params.append(args["date_to"])
    if args.get("doc_type"):
        where.append("h.DocType = ?")
        params.append(args["doc_type"])
    if args.get("employee_id"):
        where.append("h.EmployeeId = ?")
        params.append(args["employee_id"])
    return " AND ".join(where), params


def _detail_filter(args):
    where = ["1=1"]
    params = []
    if args.get("date_from"):
        where.append("h.DocDate >= ?")
        params.append(args["date_from"])
    if args.get("date_to"):
        where.append("h.DocDate <= ?")
        params.append(args["date_to"])
    if args.get("doc_type"):
        where.append("d.DocType = ?")
        params.append(args["doc_type"])
    if args.get("product_id"):
        where.append("d.ProductId = ?")
        params.append(args["product_id"])
    return " AND ".join(where), params


def _closing_filter(args):
    where = ["1=1"]
    params = []
    if args.get("date_from"):
        where.append("ClosingDate >= ?")
        params.append(args["date_from"])
    if args.get("date_to"):
        where.append("ClosingDate <= ?")
        params.append(args["date_to"])
    if args.get("product_id"):
        where.append("ProductId = ?")
        params.append(args["product_id"])
    return " AND ".join(where), params


def _run_header_query(args):
    where_sql, params = _header_filter(args)
    sql = f"""
        SELECT h.DocType, h.DocId, h.DocDate, h.EmployeeId, e.EmployeeName
        FROM v_InoutHeader h
        JOIN Employee e ON e.EmployeeId = h.EmployeeId
        WHERE {where_sql}
        ORDER BY h.DocDate DESC, h.DocId DESC
    """
    return query_all(sql, params)


def _run_detail_query(args):
    where_sql, params = _detail_filter(args)
    sql = f"""
        SELECT d.DocType, d.DocId, h.DocDate, d.LineNum, d.ProductId, d.ProductName, d.Quantity
        FROM v_InoutDetail d
        JOIN v_InoutHeader h ON h.DocType = d.DocType AND h.DocId = d.DocId
        WHERE {where_sql}
        ORDER BY h.DocDate DESC, d.DocId DESC, d.LineNum
    """
    return query_all(sql, params)


def _run_closing_query(args):
    where_sql, params = _closing_filter(args)
    sql = f"""
        SELECT ClosingDate, ProductId, ProductName, OpeningQuantity, InboundQuantity, OutboundQuantity, ClosingQuantity
        FROM v_InventoryDailyClosing
        WHERE {where_sql}
        ORDER BY ClosingDate DESC, ProductId
    """
    return query_all(sql, params)


DOC_TYPE_LABELS = {"": "全部", "IN": "入庫", "OUT": "出庫"}


def _doc_type_selectbox(key):
    return st.selectbox(
        "類別", list(DOC_TYPE_LABELS.keys()), format_func=lambda v: DOC_TYPE_LABELS[v], key=key
    )


def _optional_select(label, rows, id_key, name_key, key):
    options = {"": "全部"} | {r[id_key]: f"{r[id_key]} - {r[name_key]}" for r in rows}
    selected = st.selectbox(label, list(options.keys()), format_func=lambda v: options[v], key=key)
    return selected


def _export_button(label, filename, columns, rows):
    buffer = export_report(label, columns, rows)
    st.download_button(
        "📥 匯出 Excel", data=buffer.getvalue(), file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"export_{filename}",
    )


def render_inout_header():
    st.title("入出單據")
    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")

    col1, col2, col3, col4 = st.columns(4)
    date_from = col1.date_input("開始日期", value=None, key="rh_date_from")
    date_to = col2.date_input("結束日期", value=None, key="rh_date_to")
    with col3:
        doc_type = _doc_type_selectbox("rh_doc_type")
    with col4:
        employee_id = _optional_select("經手人", employees, "EmployeeId", "EmployeeName", "rh_employee")

    args = {"date_from": date_from, "date_to": date_to, "doc_type": doc_type, "employee_id": employee_id}
    rows = _run_header_query(args)

    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
        columns = [
            ("類別", "DocType"), ("單號", "DocId"), ("日期", "DocDate"),
            ("經手人編號", "EmployeeId"), ("經手人姓名", "EmployeeName"),
        ]
        _export_button("入出單據", "inout_header.xlsx", columns, rows)
    else:
        st.info("查無資料")


def render_inout_detail():
    st.title("入出明細")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")

    col1, col2, col3, col4 = st.columns(4)
    date_from = col1.date_input("開始日期", value=None, key="rd_date_from")
    date_to = col2.date_input("結束日期", value=None, key="rd_date_to")
    with col3:
        doc_type = _doc_type_selectbox("rd_doc_type")
    with col4:
        product_id = _optional_select("物料", products, "ProductId", "ProductName", "rd_product")

    args = {"date_from": date_from, "date_to": date_to, "doc_type": doc_type, "product_id": product_id}
    rows = _run_detail_query(args)

    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
        columns = [
            ("類別", "DocType"), ("單號", "DocId"), ("日期", "DocDate"), ("行號", "LineNum"),
            ("物料編號", "ProductId"), ("物料名稱", "ProductName"), ("數量", "Quantity"),
        ]
        _export_button("入出明細", "inout_detail.xlsx", columns, rows)
    else:
        st.info("查無資料")


def render_daily_closing():
    st.title("日結餘額表")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")

    col1, col2, col3 = st.columns(3)
    date_from = col1.date_input("開始日期", value=None, key="rc_date_from")
    date_to = col2.date_input("結束日期", value=None, key="rc_date_to")
    with col3:
        product_id = _optional_select("物料", products, "ProductId", "ProductName", "rc_product")

    args = {"date_from": date_from, "date_to": date_to, "product_id": product_id}
    rows = _run_closing_query(args)

    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
        columns = [
            ("日期", "ClosingDate"), ("物料編號", "ProductId"), ("物料名稱", "ProductName"),
            ("期初庫存", "OpeningQuantity"), ("入庫數量", "InboundQuantity"),
            ("出庫數量", "OutboundQuantity"), ("期末庫存", "ClosingQuantity"),
        ]
        _export_button("日結餘額表", "daily_closing.xlsx", columns, rows)
    else:
        st.info("查無資料")


