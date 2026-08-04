from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.db import db_cursor, query_all, query_one
from app.utils.excel_export import export_document, send_excel
from app.utils.ids import generate_doc_id

bp = Blueprint("outbound", __name__, url_prefix="/outbound")


def _parse_lines(form):
    product_ids = form.getlist("line_product_id")
    quantities = form.getlist("line_quantity")
    lines = []
    for pid, qty in zip(product_ids, quantities):
        pid = pid.strip()
        qty = qty.strip()
        if not pid or not qty:
            continue
        lines.append((pid, qty))
    return lines


@bp.route("/")
def list_view():
    rows = query_all(
        """
        SELECT h.OutboundId, h.OutboundDate, h.EmployeeId, e.EmployeeName,
               (SELECT COUNT(*) FROM OutboundDetail d WHERE d.OutboundId = h.OutboundId) AS LineCount
        FROM OutboundHeader h
        JOIN Employee e ON e.EmployeeId = h.EmployeeId
        ORDER BY h.OutboundId DESC
        """
    )
    return render_template("outbound/list.html", rows=rows)


@bp.route("/new", methods=["GET", "POST"])
def create_view():
    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")

    if request.method == "POST":
        outbound_date_str = request.form["outbound_date"]
        employee_id = request.form["employee_id"]
        lines = _parse_lines(request.form)

        if not lines:
            flash("至少要有一筆明細", "error")
            return render_template("outbound/form.html", mode="new", employees=employees, products=products, form=request.form, lines=[])

        outbound_date = date.fromisoformat(outbound_date_str)
        outbound_id = generate_doc_id("OutboundHeader", "OutboundId", "OUT", outbound_date)

        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO OutboundHeader (OutboundId, OutboundDate, EmployeeId) VALUES (?, ?, ?)",
                (outbound_id, outbound_date, employee_id),
            )
            for line_num, (product_id, qty) in enumerate(lines, start=1):
                prod = query_one("SELECT ProductName FROM Product WHERE ProductId = ?", (product_id,))
                if not prod:
                    raise ValueError(f"物料 {product_id} 不存在")
                cur.execute(
                    "INSERT INTO OutboundDetail (OutboundId, LineNum, ProductId, ProductName, Quantity) VALUES (?, ?, ?, ?, ?)",
                    (outbound_id, line_num, product_id, prod["ProductName"], qty),
                )

        flash(f"出庫單 {outbound_id} 新增成功", "success")
        return redirect(url_for("outbound.list_view"))

    return render_template("outbound/form.html", mode="new", employees=employees, products=products, form={}, lines=[], today=date.today().isoformat())


@bp.route("/<outbound_id>/edit", methods=["GET", "POST"])
def edit_view(outbound_id):
    header = query_one("SELECT * FROM OutboundHeader WHERE OutboundId = ?", (outbound_id,))
    if not header:
        flash("找不到該出庫單", "error")
        return redirect(url_for("outbound.list_view"))

    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")

    if request.method == "POST":
        outbound_date_str = request.form["outbound_date"]
        employee_id = request.form["employee_id"]
        lines = _parse_lines(request.form)

        if not lines:
            flash("至少要有一筆明細", "error")
            existing_lines = query_all("SELECT * FROM OutboundDetail WHERE OutboundId = ? ORDER BY LineNum", (outbound_id,))
            return render_template("outbound/form.html", mode="edit", outbound_id=outbound_id, employees=employees, products=products, form=request.form, lines=existing_lines)

        outbound_date = date.fromisoformat(outbound_date_str)

        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE OutboundHeader SET OutboundDate = ?, EmployeeId = ? WHERE OutboundId = ?",
                (outbound_date, employee_id, outbound_id),
            )
            cur.execute("DELETE FROM OutboundDetail WHERE OutboundId = ?", (outbound_id,))
            for line_num, (product_id, qty) in enumerate(lines, start=1):
                prod = query_one("SELECT ProductName FROM Product WHERE ProductId = ?", (product_id,))
                if not prod:
                    raise ValueError(f"物料 {product_id} 不存在")
                cur.execute(
                    "INSERT INTO OutboundDetail (OutboundId, LineNum, ProductId, ProductName, Quantity) VALUES (?, ?, ?, ?, ?)",
                    (outbound_id, line_num, product_id, prod["ProductName"], qty),
                )

        flash("更新成功", "success")
        return redirect(url_for("outbound.list_view"))

    lines = query_all("SELECT * FROM OutboundDetail WHERE OutboundId = ? ORDER BY LineNum", (outbound_id,))
    return render_template("outbound/form.html", mode="edit", outbound_id=outbound_id, employees=employees, products=products, form=header, lines=lines)


@bp.route("/<outbound_id>/delete", methods=["POST"])
def delete_view(outbound_id):
    # 明細要先手動刪除、header 最後刪：理由同 inbound.delete_view，見 CLAUDE.md「已知坑」。
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM OutboundDetail WHERE OutboundId = ?", (outbound_id,))
        cur.execute("DELETE FROM OutboundHeader WHERE OutboundId = ?", (outbound_id,))
    flash(f"出庫單 {outbound_id} 已刪除", "success")
    return redirect(url_for("outbound.list_view"))


@bp.route("/<outbound_id>/export")
def export_view(outbound_id):
    header = query_one(
        """
        SELECT h.OutboundId, h.OutboundDate, h.EmployeeId, e.EmployeeName
        FROM OutboundHeader h JOIN Employee e ON e.EmployeeId = h.EmployeeId
        WHERE h.OutboundId = ?
        """,
        (outbound_id,),
    )
    if not header:
        flash("找不到該出庫單", "error")
        return redirect(url_for("outbound.list_view"))

    lines = query_all("SELECT LineNum, ProductId, ProductName, Quantity FROM OutboundDetail WHERE OutboundId = ? ORDER BY LineNum", (outbound_id,))

    header_fields = [
        ("單號", header["OutboundId"]),
        ("日期", str(header["OutboundDate"])),
        ("經手人", f"{header['EmployeeName']} ({header['EmployeeId']})"),
    ]
    detail_columns = [("行號", "LineNum"), ("物料編號", "ProductId"), ("物料名稱", "ProductName"), ("數量", "Quantity")]

    buffer = export_document("出庫單", header_fields, detail_columns, lines)
    return send_excel(buffer, f"{outbound_id}.xlsx")
