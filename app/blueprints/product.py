import pyodbc
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.db import execute, query_all, query_one

bp = Blueprint("product", __name__, url_prefix="/product")


@bp.route("/")
def list_view():
    rows = query_all("SELECT ProductId, ProductName, StockBalance FROM Product ORDER BY ProductId")
    return render_template("product/list.html", rows=rows)


@bp.route("/new", methods=["GET", "POST"])
def create_view():
    if request.method == "POST":
        product_id = request.form["product_id"].strip()
        name = request.form["product_name"].strip()
        stock = request.form["stock_balance"].strip()
        if not product_id or not name:
            flash("物料編號與名稱為必填", "error")
            return render_template("product/form.html", mode="new", form=request.form)
        try:
            execute(
                "INSERT INTO Product (ProductId, ProductName, StockBalance) VALUES (?, ?, ?)",
                (product_id, name, stock or 0),
            )
        except pyodbc.IntegrityError:
            flash(f"物料編號 {product_id} 已存在", "error")
            return render_template("product/form.html", mode="new", form=request.form)
        flash("新增成功", "success")
        return redirect(url_for("product.list_view"))
    return render_template("product/form.html", mode="new", form={})


@bp.route("/<product_id>/edit", methods=["GET", "POST"])
def edit_view(product_id):
    row = query_one("SELECT * FROM Product WHERE ProductId = ?", (product_id,))
    if not row:
        flash("找不到該物料", "error")
        return redirect(url_for("product.list_view"))

    if request.method == "POST":
        name = request.form["product_name"].strip()
        stock = request.form["stock_balance"].strip()
        if not name:
            flash("名稱為必填", "error")
            return render_template("product/form.html", mode="edit", form=request.form, product_id=product_id)
        execute(
            "UPDATE Product SET ProductName = ?, StockBalance = ? WHERE ProductId = ?",
            (name, stock or 0, product_id),
        )
        flash("更新成功", "success")
        return redirect(url_for("product.list_view"))

    return render_template("product/form.html", mode="edit", form=row, product_id=product_id)


@bp.route("/<product_id>")
def detail_view(product_id):
    row = query_one("SELECT * FROM Product WHERE ProductId = ?", (product_id,))
    if not row:
        flash("找不到該物料", "error")
        return redirect(url_for("product.list_view"))
    details = query_all(
        "SELECT DocType, DocId, LineNum, Quantity FROM v_InoutDetail WHERE ProductId = ? ORDER BY DocId, LineNum",
        (product_id,),
    )
    return render_template("product/detail.html", row=row, details=details)


@bp.route("/<product_id>/delete", methods=["POST"])
def delete_view(product_id):
    count = query_one("SELECT COUNT(*) AS c FROM v_InoutDetail WHERE ProductId = ?", (product_id,))["c"]
    if count > 0:
        flash(f"此物料已有 {count} 筆入出明細，無法刪除", "error")
        return redirect(url_for("product.list_view"))
    try:
        execute("DELETE FROM Product WHERE ProductId = ?", (product_id,))
        flash("刪除成功", "success")
    except pyodbc.IntegrityError:
        flash("此物料仍被其他資料參照，無法刪除", "error")
    return redirect(url_for("product.list_view"))
