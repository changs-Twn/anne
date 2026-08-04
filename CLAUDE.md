# CLAUDE.md

這個 repo 裡有兩份針對同一個 `biz_anne` 資料庫的交付物，**限制不同，不要混用**：

| 交付物 | 內容 | 資料庫存取限制 |
|---|---|---|
| ERD 反推 workshop | `er_diagram.html`、`add_missing_foreign_keys.sql`、根目錄 `SKILL.md` | 唯讀，**不可執行任何 DML/DCL**（見下方「ERD workshop 任務限制」） |
| Mini ERP 檔管理系統 | `app/`、`run.py`、`sql/seed_test_data.sql`、`.claude/skills/minierp-dev/SKILL.md` | 正常 CRUD web app，本來就需要 INSERT/UPDATE/DELETE |

## 資料庫連線

| 項目 | 值 |
|---|---|
| Server | `163.17.141.61,8082`（非標準 port 的 SQL Server 2022 Developer Edition） |
| Database | `biz_anne`（從共用範本 `biz00` 用 `BACKUP DATABASE` / `RESTORE DATABASE` 複製出的個人副本） |
| Login | `nutc`（同一組帳密，`sysadmin` 權限，同伺服器上還有其他學生的副本如 `casper`、`chjer`） |
| Password | **不寫進本檔／不進 git**。密碼是課程共用的教學帳密；Mini ERP app 的真實連線資訊放在 `.env`（已 gitignore），範例格式看 `.env.example`。 |

連線務必用 **ODBC Driver 18 for SQL Server**（`pyodbc`），不要用 `pymssql`／FreeTDS ——
後者在這台機器上對 `NVARCHAR` 的中文欄位會產生亂碼（見下方「已知坑」）。

## Schema 摘要

7 個資料表，全部關聯都已經有 `FOREIGN KEY`：

```
Employee ──┬─< InboundHeader  ──< InboundDetail >── Product
           └─< OutboundHeader ──< OutboundDetail >── Product
                                  InventoryDailyClosing >── Product
```

- `InboundDetail`/`OutboundDetail` → `Product`：`NO_ACTION`（有明細就不能刪 Product）
- `InboundHeader`/`OutboundHeader` → `Employee`：`NO_ACTION`（有單據就不能刪 Employee）
- `InboundDetail` → `InboundHeader`、`OutboundDetail` → `OutboundHeader`：**CASCADE**（刪單頭會自動刪明細）

3 個報表 view（`v_InoutHeader`、`v_InoutDetail`、`v_InventoryDailyClosing`）對 `Employee` /
`Product` 有引用，但 **SQL Server 的 view 結構上不能宣告 FK**——這是唯一「沒有寫 FK」的部分，
細節看 `er_diagram.html`。

`InventoryDailyClosing` 是由 4 個 trigger（`trg_InboundDetail_DailyClosing` 等）維護的
**運算式帳本**，不要手動 INSERT / UPDATE 它，只要對 `InboundDetail` / `OutboundDetail` 做異動，
trigger 會自動算好 Opening/Inbound/Outbound/Closing 並遞延到後面的日期。

## 已知坑

- **中文亂碼**：這台機器的 git-bash `stdout` 預設編碼是 `cp950`，用 Python 印中文欄位（如
  `ProductName`、`EmployeeName`）在終端機會變成亂碼字元。**這是顯示問題，不是資料庫存的資料壞掉**。
  解法：跑 Python 前加 `PYTHONIOENCODING=utf-8`。Mini ERP app 本身透過 Flask/瀏覽器顯示中文沒有這個問題，只有終端機直接印資料時才會遇到。
- **pymssql 也會亂碼**：即使設定 `charset`，FreeTDS 對這個 DB 的 Unicode 轉換仍不正確；改用
  `pyodbc` + `ODBC Driver 18 for SQL Server` 才會正確顯示中文。
- **不要對 biz00（共用範本）下寫入指令**，所有練習/測試資料一律建立在自己的 `biz_anne`。

---

## ERD workshop 任務限制（僅適用於 `er_diagram.html` / `add_missing_foreign_keys.sql` / 根目錄 `SKILL.md` 這份交付物）

- 不可對資料庫執行任何 **DML**（INSERT/UPDATE/DELETE）或 **DCL**（GRANT/REVOKE）。
- Schema 探勘只能用唯讀查詢：`INFORMATION_SCHEMA.*`、`sys.foreign_keys`、
  `sys.foreign_key_columns`、`OBJECT_DEFINITION()`。
- 產生的補強腳本（`add_missing_foreign_keys.sql`）是文件產出物，**不要拿去執行**。

檔案對照：`er_diagram.html`（完整 ER 圖，inline SVG）、`add_missing_foreign_keys.sql`（產生但未執行的補強腳本）、根目錄 `SKILL.md`（可重用的「唯讀反推 schema／畫 ERD」操作手冊）。

---

## Mini ERP 檔管理系統

Flask + SQL Server 的迷你 ERP，二層式功能表（主數據／交易數據／報表查詢）。資料表沿用上面 schema，**不需要建 DDL**。這份交付物本來就是要做 CRUD，跟上面 ERD workshop 的唯讀限制無關。

### 啟動方式

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # 複製後填入真實的 DB_SERVER/DB_NAME/DB_UID/DB_PWD
python run.py                   # http://127.0.0.1:5000
```

### 目錄結構

```
app/
  __init__.py          create_app() factory，註冊 blueprints，把 menu.MENU 注入所有 template
  config.py             從 .env 讀取設定，組 ODBC 連線字串
  db.py                  pyodbc 連線；query_all()/query_one()/execute()/db_cursor() 是全部 SQL 存取的唯一入口
  menu.py                 二層選單的唯一定義（見下方「選單與路由對照」）
  blueprints/            每個模組一個檔案，各自管一組路由
  templates/              依模組分資料夾，base.html 是共用版型（含二層 navbar）
  static/js/detail_lines.js  入庫/出庫表單明細列的新增/刪除
  utils/excel_export.py       export_document()（單據式）/ export_report()（報表式）
  utils/ids.py                 交易單號產生規則：PREFIX + YYYYMMDD + 3碼序號
sql/seed_test_data.sql   補充測試資料腳本，IF NOT EXISTS 判斷、可重複執行、不刪既有資料
```

### 選單與路由對照

| 第一層 | 第二層 | 路由前綴 | 說明 |
|---|---|---|---|
| 主數據 | 物料管理 | `/product` | header: Product，明細唯讀來源 `v_InoutDetail` |
| 主數據 | 員工管理 | `/employee` | header: Employee，明細唯讀來源 `v_InoutHeader` |
| 交易數據 | 入庫管理 | `/inbound` | header+detail: InboundHeader/InboundDetail |
| 交易數據 | 出庫管理 | `/outbound` | header+detail: OutboundHeader/OutboundDetail |
| 報表查詢 | 入出單據 | `/reports/inout-header` | view: v_InoutHeader，查詢+匯出 |
| 報表查詢 | 入出明細 | `/reports/inout-detail` | view: v_InoutDetail，查詢+匯出 |

### 資料庫存取慣例

- **一律用 `?` 參數化查詢**，不得用字串拼接組 SQL（防注入）。所有 SQL 都走 `app/db.py` 的 helper。
- **主檔刪除保護**：Product/Employee 刪除前先查明細筆數（`v_InoutDetail`/`v_InoutHeader`），有資料就擋下並 flash 錯誤訊息；DB 的 FK（`NO_ACTION`）是第二道防線。
- **交易單刪除**：InboundHeader/OutboundHeader 刪除會靠 FK `CASCADE` 自動清掉對應明細，不需要手動兩段式刪除。
- **交易單編輯**：採「刪明細重插」，不做逐筆 diff。
- **單號產生**：`app/utils/ids.generate_doc_id()`，格式 `IN`/`OUT` + 日期 + 3碼序號，跟現有資料格式一致（例：`IN20260714001`）。

### 已知限制

- Excel 匯出用 openpyxl，純記憶體 BytesIO，不落地到 `exports/`（該資料夾目前保留給未來需要落地檔案時使用）。
- 沒有登入/權限機制，屬於單一使用者的內部工具。
