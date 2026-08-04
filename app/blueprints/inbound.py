from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.db import db_cursor, query_all, query_one
from app.utils.excel_export import export_document, send_excel
from app.utils.ids import generate_doc_id

bp = Blueprint("inbound", __name__, url_prefix="/inbound")


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
        SELECT h.InboundId, h.InboundDate, h.EmployeeId, e.EmployeeName,
               (SELECT COUNT(*) FROM InboundDetail d WHERE d.InboundId = h.InboundId) AS LineCount
        FROM InboundHeader h
        JOIN Employee e ON e.EmployeeId = h.EmployeeId
        ORDER BY h.InboundId DESC
        """
    )
    return render_template("inbound/list.html", rows=rows)


@bp.route("/new", methods=["GET", "POST"])
def create_view():
    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")

    if request.method == "POST":
        inbound_date_str = request.form["inbound_date"]
        employee_id = request.form["employee_id"]
        lines = _parse_lines(request.form)

        if not lines:
            flash("至少要有一筆明細", "error")
            return render_template("inbound/form.html", mode="new", employees=employees, products=products, form=request.form, lines=[])

        inbound_date = date.fromisoformat(inbound_date_str)
        inbound_id = generate_doc_id("InboundHeader", "InboundId", "IN", inbound_date)

        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO InboundHeader (InboundId, InboundDate, EmployeeId) VALUES (?, ?, ?)",
                (inbound_id, inbound_date, employee_id),
            )
            for line_num, (product_id, qty) in enumerate(lines, start=1):
                prod = query_one("SELECT ProductName FROM Product WHERE ProductId = ?", (product_id,))
                if not prod:
                    raise ValueError(f"物料 {product_id} 不存在")
                cur.execute(
                    "INSERT INTO InboundDetail (InboundId, LineNum, ProductId, ProductName, Quantity) VALUES (?, ?, ?, ?, ?)",
                    (inbound_id, line_num, product_id, prod["ProductName"], qty),
                )

        flash(f"入庫單 {inbound_id} 新增成功", "success")
        return redirect(url_for("inbound.list_view"))

    return render_template("inbound/form.html", mode="new", employees=employees, products=products, form={}, lines=[], today=date.today().isoformat())


@bp.route("/<inbound_id>/edit", methods=["GET", "POST"])
def edit_view(inbound_id):
    header = query_one("SELECT * FROM InboundHeader WHERE InboundId = ?", (inbound_id,))
    if not header:
        flash("找不到該入庫單", "error")
        return redirect(url_for("inbound.list_view"))

    employees = query_all("SELECT EmployeeId, EmployeeName FROM Employee ORDER BY EmployeeId")
    products = query_all("SELECT ProductId, ProductName FROM Product ORDER BY ProductId")

    if request.method == "POST":
        inbound_date_str = request.form["inbound_date"]
        employee_id = request.form["employee_id"]
        lines = _parse_lines(request.form)

        if not lines:
            flash("至少要有一筆明細", "error")
            existing_lines = query_all("SELECT * FROM InboundDetail WHERE InboundId = ? ORDER BY LineNum", (inbound_id,))
            return render_template("inbound/form.html", mode="edit", inbound_id=inbound_id, employees=employees, products=products, form=request.form, lines=existing_lines)

        inbound_date = date.fromisoformat(inbound_date_str)

        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE InboundHeader SET InboundDate = ?, EmployeeId = ? WHERE InboundId = ?",
                (inbound_date, employee_id, inbound_id),
            )
            cur.execute("DELETE FROM InboundDetail WHERE InboundId = ?", (inbound_id,))
            for line_num, (product_id, qty) in enumerate(lines, start=1):
                prod = query_one("SELECT ProductName FROM Product WHERE ProductId = ?", (product_id,))
                if not prod:
                    raise ValueError(f"物料 {product_id} 不存在")
                cur.execute(
                    "INSERT INTO InboundDetail (InboundId, LineNum, ProductId, ProductName, Quantity) VALUES (?, ?, ?, ?, ?)",
                    (inbound_id, line_num, product_id, prod["ProductName"], qty),
                )

        flash("更新成功", "success")
        return redirect(url_for("inbound.list_view"))

    lines = query_all("SELECT * FROM InboundDetail WHERE InboundId = ? ORDER BY LineNum", (inbound_id,))
    return render_template("inbound/form.html", mode="edit", inbound_id=inbound_id, employees=employees, products=products, form=header, lines=lines)


@bp.route("/<inbound_id>/delete", methods=["POST"])
def delete_view(inbound_id):
    # 明細要先手動刪除、header 最後刪：DB 的 trg_InboundDetail_DailyClosing 在算日結餘額 delta 時
    # 會 JOIN InboundHeader 取日期，若靠 FK CASCADE 讓 header 先被刪掉，
    # 明細的 AFTER DELETE trigger 觸發時 header 已經不存在，JOIN 會是空集合，
    # 日結餘額表就不會被回沖（驗證過的真實案例，見 CLAUDE.md「已知坑」）。
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM InboundDetail WHERE InboundId = ?", (inbound_id,))
        cur.execute("DELETE FROM InboundHeader WHERE InboundId = ?", (inbound_id,))
    flash(f"入庫單 {inbound_id} 已刪除", "success")
    return redirect(url_for("inbound.list_view"))


@bp.route("/<inbound_id>/export")
def export_view(inbound_id):
    header = query_one(
        """
        SELECT h.InboundId, h.InboundDate, h.EmployeeId, e.EmployeeName
        FROM InboundHeader h JOIN Employee e ON e.EmployeeId = h.EmployeeId
        WHERE h.InboundId = ?
        """,
        (inbound_id,),
    )
    if not header:
        flash("找不到該入庫單", "error")
        return redirect(url_for("inbound.list_view"))

    lines = query_all("SELECT LineNum, ProductId, ProductName, Quantity FROM InboundDetail WHERE InboundId = ? ORDER BY LineNum", (inbound_id,))

    header_fields = [
        ("單號", header["InboundId"]),
        ("日期", str(header["InboundDate"])),
        ("經手人", f"{header['EmployeeName']} ({header['EmployeeId']})"),
    ]
    detail_columns = [("行號", "LineNum"), ("物料編號", "ProductId"), ("物料名稱", "ProductName"), ("數量", "Quantity")]

    buffer = export_document("入庫單", header_fields, detail_columns, lines)
    return send_excel(buffer, f"{inbound_id}.xlsx")
