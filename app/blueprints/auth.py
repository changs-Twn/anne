from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.db import query_one

bp = Blueprint("auth", __name__)

SUPER_ID = "Super"
SUPER_PASSWORD = "Super"


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        employee_id = request.form.get("employee_id", "").strip()
        password = request.form.get("password", "").strip()

        if employee_id == SUPER_ID and password == SUPER_PASSWORD:
            session["employee_id"] = SUPER_ID
            session["employee_name"] = "Super"
            session["is_super"] = True
            return redirect(request.args.get("next") or url_for("index"))

        row = query_one(
            "SELECT EmployeeId, EmployeeName, Password FROM Employee WHERE EmployeeId = ?",
            (employee_id,),
        )
        if row and row["Password"].strip() == password:
            session["employee_id"] = row["EmployeeId"]
            session["employee_name"] = row["EmployeeName"]
            session["is_super"] = False
            return redirect(request.args.get("next") or url_for("index"))

        flash("員工編號或密碼錯誤", "error")
        return render_template("auth/login.html", employee_id=employee_id)

    return render_template("auth/login.html", employee_id="")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
