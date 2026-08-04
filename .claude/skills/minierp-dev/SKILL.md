---
name: minierp-dev
description: Use when adding or modifying modules in this Mini ERP Flask app (Project5) — new master-data module, new transaction module, new report, menu changes, or Excel export changes. Captures the conventions the existing product/employee/inbound/outbound/reports modules follow so new code stays consistent.
---

# Mini ERP 開發慣例

這是一個 Flask + SQL Server (`biz_anne`) 的二層選單迷你 ERP。資料表都已存在於資料庫，不要生成 DDL；只透過 `app/db.py` 的 helper 存取。

## 新增一個「主數據」模組（像 Product/Employee）

1. 在 `app/blueprints/<name>.py` 建立 blueprint，四個路由：`/` (list)、`/new` (GET+POST)、`/<id>/edit` (GET+POST)、`/<id>` (detail，唯讀明細)、`/<id>/delete` (POST)。
2. 刪除前一定要先查有沒有關聯明細（仿照 `product.py` 的 `delete_view`：`SELECT COUNT(*) ... WHERE <FK欄位> = ?`），有資料就 `flash(..., "error")` 並導回列表，不要直接讓 DB 的 FK 例外炸出 500。
3. 明細畫面只顯示，不給編輯/刪除按鈕。
4. 在 `app/__init__.py` 註冊 blueprint，在 `app/menu.py` 對應的 `children` 陣列加一筆 `{"title": ..., "endpoint": "<name>.list_view"}`。
5. templates 放 `app/templates/<name>/list.html`、`form.html`、`detail.html`，直接 `{% extends "base.html" %}`。

## 新增一個「交易數據」模組（像 Inbound/Outbound）

1. header+detail 一起在同一個表單送出，明細列用 `app/static/js/detail_lines.js`（`detail-lines-body` + `<template id="detail-line-template">` 的 pattern，照抄 `inbound/form.html`）。
2. 新增/編輯都要包在同一個 DB transaction 裡：`with db_cursor(commit=True) as cur:`，先處理 header，再處理 detail。編輯採「刪明細重插」（`DELETE FROM xxxDetail WHERE ...` 再重新 INSERT），不要做逐筆 diff。
3. 單號用 `app/utils/ids.generate_doc_id(table, id_column, prefix, date_obj)` 產生，不要讓使用者手動輸入單號。
4. **刪除一律先手動 `DELETE FROM xxxDetail WHERE ...`，header 放最後刪**——不要靠 FK 的
   `ON DELETE CASCADE` 讓刪 header 帶著刪明細。雖然 InboundDetail/OutboundDetail 對 Header
   是 CASCADE，但 `trg_InboundDetail_DailyClosing`/`trg_OutboundDetail_DailyClosing` 算日結
   餘額 delta 時要 `JOIN` 回 Header 拿日期；CASCADE 情境下明細的 `AFTER DELETE` trigger 觸發時
   header 那一列已經被刪掉了，JOIN 對不到、delta 算成空的，`InventoryDailyClosing` 就不會被
   回沖，留下錯誤餘額（實測驗證過，見 `CLAUDE.md`「已知坑」）。先刪明細時 header 還在，
   trigger 才能正確算出負的 delta。
5. 一定要提供 `/<id>/export` 路由，用 `app/utils/excel_export.export_document()` 產生「單據式」Excel（合併標題 + 單頭欄位 + 明細表格），不是平面表格。

## 新增一個「報表查詢」模組（像 Reports）

1. 一個報表至少要有兩個路由：查詢頁 (`GET`，帶篩選表單) 和匯出頁 (`GET .../export`，同樣的篩選條件轉成 Excel)——這是規格要求的「查詢＋匯出至少二個功能」。
2. 篩選條件的 SQL 組裝要照 `reports.py` 的 `_header_filter()`/`_detail_filter()` pattern：用 `WHERE 1=1` + 動態 append 條件字串 + **對應的參數化 `params` list**，欄位名稱是寫死的常數、值一定要走 `?` 參數，不要把使用者輸入直接接進 SQL 字串。
3. 匯出用 `app/utils/excel_export.export_report()`（平面表格，不是單據式）。
4. 查詢頁的匯出按鈕要用 `url_for('....export', **args)` 把目前的篩選條件原樣帶過去，不要讓匯出結果跟畫面上看到的不一致。

## Excel 匯出

- `app/utils/excel_export.py` 只有兩個函式：`export_document()`（單據式，交易模組用）、`export_report()`（平面表格，報表模組用）。兩者都回傳 `BytesIO`，用 `send_excel(buffer, filename)` 包成 Flask response。不要另外發明第三種格式，除非規格明確要求。

## Jinja 選單陷阱

`app/menu.py` 的巢狀 key 叫 `children`，不是 `items`——因為 dict 有內建的 `.items()` 方法，Jinja 屬性解析在模板裡對 `dict.items` 會拿到 bound method 而不是 list，之前踩過這個坑（`TypeError: 'builtin_function_or_method' object is not iterable`）。往選單資料結構加新 key 時要避開 `items`/`keys`/`values` 這類會跟 dict 方法撞名的字。
