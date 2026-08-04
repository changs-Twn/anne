import re

import pyodbc
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.db import execute, query_all, query_one

bp = Blueprint("employee", __name__, url_prefix="/employee")

PASSWORD_RE = re.compile(r"^[A-Za-z0-9]{6}$")
DEFAULT_PASSWORD = "123456"


@bp.route("/")
def list_view():
    rows = query_all("SELECT EmployeeId, EmployeeName, Email FROM Employee ORDER BY EmployeeId")
    return render_template("employee/list.html", rows=rows)


@bp.route("/new", methods=["GET", "POST"])
def create_view():
    if request.method == "POST":
        employee_id = request.form["employee_id"].strip()
        name = request.form["employee_name"].strip()
        email = request.form["email"].strip() or None
        password = request.form.get("password", "").strip() or DEFAULT_PASSWORD
        if not employee_id or not name:
            flash("員工編號與姓名為必填", "error")
            return render_template("employee/form.html", mode="new", form=request.form)
        if not PASSWORD_RE.match(password):
            flash("密碼必須是 6 碼英數字", "error")
            return render_template("employee/form.html", mode="new", form=request.form)
        try:
            execute(
                "INSERT INTO Employee (EmployeeId, EmployeeName, Email, Password) VALUES (?, ?, ?, ?)",
                (employee_id, name, email, password),
            )
        except pyodbc.IntegrityError:
            flash(f"員工編號 {employee_id} 已存在", "error")
            return render_template("employee/form.html", mode="new", form=request.form)
        flash("新增成功", "success")
        return redirect(url_for("employee.list_view"))
    return render_template("employee/form.html", mode="new", form={}, default_password=DEFAULT_PASSWORD)


@bp.route("/<employee_id>/edit", methods=["GET", "POST"])
def edit_view(employee_id):
    row = query_one("SELECT * FROM Employee WHERE EmployeeId = ?", (employee_id,))
    if not row:
        flash("找不到該員工", "error")
        return redirect(url_for("employee.list_view"))

    if request.method == "POST":
        name = request.form["employee_name"].strip()
        email = request.form["email"].strip() or None
        password = request.form.get("password", "").strip()
        if not name:
            flash("姓名為必填", "error")
            return render_template("employee/form.html", mode="edit", form=request.form, employee_id=employee_id)
        if not PASSWORD_RE.match(password):
            flash("密碼必須是 6 碼英數字", "error")
            return render_template("employee/form.html", mode="edit", form=request.form, employee_id=employee_id)
        execute(
            "UPDATE Employee SET EmployeeName = ?, Email = ?, Password = ? WHERE EmployeeId = ?",
            (name, email, password, employee_id),
        )
        flash("更新成功", "success")
        return redirect(url_for("employee.list_view"))

    return render_template("employee/form.html", mode="edit", form=row, employee_id=employee_id)


@bp.route("/<employee_id>")
def detail_view(employee_id):
    row = query_one("SELECT * FROM Employee WHERE EmployeeId = ?", (employee_id,))
    if not row:
        flash("找不到該員工", "error")
        return redirect(url_for("employee.list_view"))
    details = query_all(
        "SELECT DocType, DocId, DocDate FROM v_InoutHeader WHERE EmployeeId = ? ORDER BY DocDate DESC, DocId",
        (employee_id,),
    )
    return render_template("employee/detail.html", row=row, details=details)


@bp.route("/<employee_id>/delete", methods=["POST"])
def delete_view(employee_id):
    count = query_one("SELECT COUNT(*) AS c FROM v_InoutHeader WHERE EmployeeId = ?", (employee_id,))["c"]
    if count > 0:
        flash(f"此員工已有 {count} 筆入出單據，無法刪除", "error")
        return redirect(url_for("employee.list_view"))
    try:
        execute("DELETE FROM Employee WHERE EmployeeId = ?", (employee_id,))
        flash("刪除成功", "success")
    except pyodbc.IntegrityError:
        flash("此員工仍被其他資料參照，無法刪除", "error")
    return redirect(url_for("employee.list_view"))
