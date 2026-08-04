from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.blueprints.employee import DEFAULT_PASSWORD, PASSWORD_RE
from app.db import execute, query_one

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
            # 密碼還是預設值 → 視為第一次登入，提示（可跳過）改密碼一次
            session["prompt_password_change"] = password == DEFAULT_PASSWORD
            return redirect(request.args.get("next") or url_for("index"))

        flash("員工編號或密碼錯誤", "error")
        return render_template("auth/login.html", employee_id=employee_id)

    return render_template("auth/login.html", employee_id="")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/change-password", methods=["POST"])
def change_password():
    if not session.get("employee_id") or session.get("is_super"):
        return redirect(url_for("index"))

    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if new_password != confirm_password:
        flash("兩次輸入的密碼不一致", "error")
    elif not PASSWORD_RE.match(new_password):
        flash("密碼必須是 6 碼英數字", "error")
    else:
        execute("UPDATE Employee SET Password = ? WHERE EmployeeId = ?", (new_password, session["employee_id"]))
        flash("密碼已更新", "success")

    return redirect(request.referrer or url_for("index"))
