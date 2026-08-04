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

**`Employee.Password`**（Mini ERP 開發期間新增的欄位，`er_diagram.html`/
`add_missing_foreign_keys.sql` 是舊快照、還沒反映這個欄位，不用回頭改那兩份唯讀交付物）：
`CHAR(6) NOT NULL DEFAULT '123456'`，CHECK constraint `CK_Employee_Password` 強制內容只能是
`[0-9A-Za-z]`（且必須恰好 6 個非空白字元，否則 `CHAR` 補的空白會被 CHECK 擋下）。新增/編輯員工
的表單、`app/blueprints/employee.py` 都已經同步支援這個欄位。

## 已知坑

- **中文亂碼**：這台機器的 git-bash `stdout` 預設編碼是 `cp950`，用 Python 印中文欄位（如
  `ProductName`、`EmployeeName`）在終端機會變成亂碼字元。**這是顯示問題，不是資料庫存的資料壞掉**。
  解法：跑 Python 前加 `PYTHONIOENCODING=utf-8`。Mini ERP app 本身透過 Flask/瀏覽器顯示中文沒有這個問題，只有終端機直接印資料時才會遇到。
- **pymssql 也會亂碼**：即使設定 `charset`，FreeTDS 對這個 DB 的 Unicode 轉換仍不正確；改用
  `pyodbc` + `ODBC Driver 18 for SQL Server` 才會正確顯示中文。
- **不要對 biz00（共用範本）下寫入指令**，所有練習/測試資料一律建立在自己的 `biz_anne`。
- **InventoryDailyClosing 的 CASCADE 刪除坑**：`trg_InboundDetail_DailyClosing`/`trg_OutboundDetail_DailyClosing`
  算 delta 時會 `JOIN InboundHeader`/`OutboundHeader` 取日期。如果靠 FK 的 `ON DELETE CASCADE`
  讓刪 header 帶著刪明細，明細的 `AFTER DELETE` trigger 觸發時 header 那一列已經被刪掉了，
  JOIN 對不到東西、算出空 delta，日結餘額表就不會被回沖，資料會悄悄留下錯誤餘額（實測驗證過的
  真實案例，不是猜測）。**因此 Mini ERP app 的 inbound/outbound 刪除一律先手動
  `DELETE FROM xxxDetail`、header 放最後刪**（見 `app/blueprints/inbound.py` /
  `outbound.py` 的 `delete_view()`），不要改回單純刪 header 靠 CASCADE。

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
  __init__.py          create_app() factory，註冊 blueprints，把 menu.MENU 注入所有 template，掛全站登入檢查（見下方「登入」）
  config.py             從 .env 讀取設定，組 ODBC 連線字串
  db.py                  pyodbc 連線；query_all()/query_one()/execute()/db_cursor() 是全部 SQL 存取的唯一入口
  menu.py                 二層選單的唯一定義（見下方「選單與路由對照」）
  blueprints/            每個模組一個檔案，各自管一組路由（auth.py 是登入/登出，其餘都被全站登入檢查保護）
  templates/              依模組分資料夾，base.html 是共用版型（含二層 navbar），auth/login.html 是獨立頁面不套 base.html
  static/js/detail_lines.js  入庫/出庫表單明細列的新增/刪除
  utils/excel_export.py       export_document()（單據式）/ export_report()（報表式）
  utils/ids.py                 交易單號產生規則：PREFIX + YYYYMMDD + 3碼序號
sql/seed_test_data.sql   補充測試資料腳本，IF NOT EXISTS 判斷、可重複執行、不刪既有資料
```

### 登入

`app/__init__.py` 的 `before_request` hook會擋下所有請求，`session` 沒有 `employee_id` 就導到
`/login?next=<原本要去的路徑>`；只有 `static`、`auth.login`、`auth.logout` 這三個 endpoint 不受檢查
（見 `PUBLIC_ENDPOINTS`）。新增 blueprint／路由**不需要自己加登入檢查**，全站已經統一擋在
`before_request` 這一層。

驗證邏輯在 `app/blueprints/auth.py`：
- `EmployeeId='Super'` 且 `Password='Super'`（字面值，不查資料庫）→ 視為最高權限登入，`session["is_super"] = True`。
- 其餘輸入 → 對 `Employee` 表比對 `EmployeeId` + `Password`（就是前面新增的那個 `CHAR(6)` 欄位）。
- `session["is_super"]` 目前只用在員工管理模組的權限判斷（見下一節）；其他模組（物料/入庫/出庫/報表）
  對所有已登入使用者一視同仁，沒有額外限制。之後如果其他模組也要分權限，一樣是拿這個 flag 判斷。

### 員工管理的存取權限

只有 Super 能看到「+ 新增員工」按鈕、能新增員工（`employee.create_view` 一開頭就擋非 Super）。
一般使用者只能查看/編輯/刪除**自己那筆**紀錄，其他人的資料一律擋下（`employee.py` 的
`_can_access(employee_id)` = `session["is_super"] or session["employee_id"] == employee_id`，
`detail_view`/`edit_view`/`delete_view` 都在最前面呼叫這個檢查）。列表頁 (`employee/list.html`)
還是顯示全部同事，只是別人那一列的操作按鈕換成 `—`，不能點；直接改網址存取別人的
`/employee/<id>`、`/employee/<id>/edit`、`/employee/<id>/delete` 一樣會被伺服器端擋下，不是只
藏 UI。如果使用者刪除的正好是自己的帳號，`delete_view` 會順便清空 session、導回 `/login`
（帳號都刪了，繼續掛著登入狀態沒意義）。

### 首次登入改密碼提示

非 Super 帳號登入時，若密碼仍等於預設值 `123456`（見 `app/blueprints/employee.py` 的
`DEFAULT_PASSWORD`），會在 `session["prompt_password_change"]` 設一個**一次性旗標**。
`app/__init__.py` 的 `inject_password_prompt` context processor 用 `session.pop(...)`
讀取並清除這個旗標，所以登入後**只有第一次載入的頁面**會把 `show_password_prompt` 傳給 template，
`base.html` 看到這個變數是 True 才會在頁面載入時自動彈出 Bootstrap modal（`#passwordChangeModal`）。

這個提示**可以跳過**（「稍後再說」按鈕純前端 dismiss，不會再打一次後端），純粹提醒、不強制、不像
`/login` 那樣用 `before_request` 擋。真的要送新密碼是走 `POST /change-password`
（`auth.change_password`），驗證規則跟員工編輯表單一樣（6 碼英數字 + 兩次輸入要一致），
成功後直接 `UPDATE Employee SET Password=?`。如果使用者又把密碼改回 `123456`，下次登入一樣會
再跳出提示——這是預期行為，沒有特別排除。

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
