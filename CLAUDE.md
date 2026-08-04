# Mini ERP 檔管理系統

Flask + SQL Server 的迷你 ERP，二層式功能表（主數據／交易數據／報表查詢），資料庫使用既有的 `biz_anne`（不需要建 DDL，所有資料表已存在）。

## 啟動方式

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # 複製後填入真實的 DB_SERVER/DB_NAME/DB_UID/DB_PWD
python run.py                   # http://127.0.0.1:5000
```

`.env` 內含真實連線資訊，已加入 `.gitignore`，不會進版控。連線需要 `ODBC Driver 18 for SQL Server`。

## 目錄結構

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

## 選單與路由對照

| 第一層 | 第二層 | 路由前綴 | 說明 |
|---|---|---|---|
| 主數據 | 物料管理 | `/product` | header: Product，明細唯讀來源 `v_InoutDetail` |
| 主數據 | 員工管理 | `/employee` | header: Employee，明細唯讀來源 `v_InoutHeader` |
| 交易數據 | 入庫管理 | `/inbound` | header+detail: InboundHeader/InboundDetail |
| 交易數據 | 出庫管理 | `/outbound` | header+detail: OutboundHeader/OutboundDetail |
| 報表查詢 | 入出單據 | `/reports/inout-header` | view: v_InoutHeader，查詢+匯出 |
| 報表查詢 | 入出明細 | `/reports/inout-detail` | view: v_InoutDetail，查詢+匯出 |

## 資料庫慣例

- **一律用 `?` 參數化查詢**，不得用字串拼接組 SQL（防注入）。所有 SQL 都走 `app/db.py` 的 helper。
- **主檔刪除保護**：Product/Employee 刪除前先查明細筆數（`v_InoutDetail`/`v_InoutHeader`），有資料就擋下並 flash 錯誤訊息；DB 的 FK（`NO_ACTION`）是第二道防線。
- **交易單刪除**：InboundHeader/OutboundHeader 刪除會靠 FK `CASCADE` 自動清掉對應明細，不需要手動兩段式刪除。
- **交易單編輯**：採「刪明細重插」，不做逐筆 diff。
- **單號產生**：`app/utils/ids.generate_doc_id()`，格式 `IN`/`OUT` + 日期 + 3碼序號，跟現有資料格式一致（例：`IN20260714001`）。

## 已知限制

- Excel 匯出用 openpyxl，純記憶體 BytesIO，不落地到 `exports/`（該資料夾目前保留給未來需要落地檔案時使用）。
- 沒有登入/權限機制，屬於單一使用者的內部工具。
