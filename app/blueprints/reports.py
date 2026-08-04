from flask import Blueprint, render_template, request

from app.db import query_all
from app.utils.excel_export import export_report, send_excel

bp = Blueprint("reports", __name__, url_prefix="/reports")


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


def _run_closing_query(args):
    where_sql, params = _closing_filter(args)
    sql = f"""
        SELECT ClosingDate, ProductId, ProductName, OpeningQuantity, InboundQuantity, OutboundQuantity, ClosingQuantity
        FROM v_InventoryDailyClosing
        WHERE {where_sql}
        ORDER BY ClosingDate DESC, ProductId
    """
    return query_all(sql, params)


@bp.route("/inout-header")
def inout_header():
    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")
    rows = _run_header_query(request.args)
    return render_template("reports/inout_header.html", rows=rows, employees=employees, args=request.args)


@bp.route("/inout-header/export")
def inout_header_export():
    rows = _run_header_query(request.args)
    columns = [("類別", "DocType"), ("單號", "DocId"), ("日期", "DocDate"), ("經手人編號", "EmployeeId"), ("經手人姓名", "EmployeeName")]
    buffer = export_report("入出單據", columns, rows)
    return send_excel(buffer, "inout_header.xlsx")


@bp.route("/inout-detail")
def inout_detail():
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")
    rows = _run_detail_query(request.args)
    return render_template("reports/inout_detail.html", rows=rows, products=products, args=request.args)


@bp.route("/inout-detail/export")
def inout_detail_export():
    rows = _run_detail_query(request.args)
    columns = [("類別", "DocType"), ("單號", "DocId"), ("日期", "DocDate"), ("行號", "LineNum"), ("物料編號", "ProductId"), ("物料名稱", "ProductName"), ("數量", "Quantity")]
    buffer = export_report("入出明細", columns, rows)
    return send_excel(buffer, "inout_detail.xlsx")


@bp.route("/daily-closing")
def daily_closing():
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")
    rows = _run_closing_query(request.args)
    return render_template("reports/daily_closing.html", rows=rows, products=products, args=request.args)


@bp.route("/daily-closing/export")
def daily_closing_export():
    rows = _run_closing_query(request.args)
    columns = [
        ("日期", "ClosingDate"),
        ("物料編號", "ProductId"),
        ("物料名稱", "ProductName"),
        ("期初庫存", "OpeningQuantity"),
        ("入庫數量", "InboundQuantity"),
        ("出庫數量", "OutboundQuantity"),
        ("期末庫存", "ClosingQuantity"),
    ]
    buffer = export_report("日結餘額表", columns, rows)
    return send_excel(buffer, "daily_closing.xlsx")
