# CLAUDE.md

這個資料夾是一份課堂 workshop 交付物：針對 `biz_anne` 資料庫，在**不執行任何 SQL DML / DCL**
的前提下，讀取 schema 反推出完整的 Entity-Relationship Diagram，並找出哪些關聯有真正的
`FOREIGN KEY` 條件約束、哪些只是隱含（沒有、也不能有 FK）。

## 資料庫連線

| 項目 | 值 |
|---|---|
| Server | `163.17.141.61,8082`（非標準 port 的 SQL Server 2022 Developer Edition） |
| Database | `biz_anne`（從共用範本 `biz00` 用 `BACKUP DATABASE` / `RESTORE DATABASE` 複製出的個人副本） |
| Login | `nutc`（同一組帳密，`sysadmin` 權限，同伺服器上還有其他學生的副本如 `casper`、`chjer`） |
| Password | **不寫進本檔／不進 git**。密碼是課程共用的教學帳密，見任務對話內容，不要 commit 明碼密碼到任何腳本或文件。 |

連線務必用 **ODBC Driver 18 for SQL Server**（`pyodbc`），不要用 `pymssql`／FreeTDS ——
後者在這台機器上對 `NVARCHAR` 的中文欄位會產生亂碼（見下方「已知坑」）。

## 檔案

| 檔案 | 內容 |
|---|---|
| `er_diagram.html` | 完整 ER 圖（inline SVG，自成一體，可直接雙擊在瀏覽器打開），含關聯總表與方法論說明 |
| `add_missing_foreign_keys.sql` | 產生但**未執行**的補強腳本；記錄哪些關聯有 FK、哪些只有 view 隱含 |
| `SKILL.md` | 可重用的「唯讀反推 schema／畫 ERD」操作手冊 |

## Schema 摘要（2026-08-04 讀取）

7 個資料表，全部關聯都已經有 `FOREIGN KEY`：

```
Employee ──┬─< InboundHeader  ──< InboundDetail >── Product
           └─< OutboundHeader ──< OutboundDetail >── Product
                                  InventoryDailyClosing >── Product
```

3 個報表 view（`v_InoutHeader`、`v_InoutDetail`、`v_InventoryDailyClosing`）對 `Employee` /
`Product` 有引用，但 **SQL Server 的 view 結構上不能宣告 FK**——這是唯一「沒有寫 FK」的部分，
細節看 `er_diagram.html`。

`InventoryDailyClosing` 是由 4 個 trigger（`trg_InboundDetail_DailyClosing` 等）維護的
**運算式帳本**，不要手動 INSERT / UPDATE 它，只要對 `InboundDetail` / `OutboundDetail` 做異動，
trigger 會自動算好 Opening/Inbound/Outbound/Closing 並遞延到後面的日期。

## 已知坑

- **中文亂碼**：這台機器的 git-bash `stdout` 預設編碼是 `cp950`，用 Python 印中文欄位（如
  `ProductName`、`EmployeeName`）在終端機會變成亂碼字元。**這是顯示問題，不是資料庫存的資料壞掉**。
  解法：跑 Python 前加 `PYTHONIOENCODING=utf-8`。
- **pymssql 也會亂碼**：即使設定 `charset`，FreeTDS 對這個 DB 的 Unicode 轉換仍不正確；改用
  `pyodbc` + `ODBC Driver 18 for SQL Server` 才會正確顯示中文。
- **不要對 biz00（共用範本）下寫入指令**，所有練習/測試資料一律建立在自己的 `biz_anne`。

## 任務限制（務必遵守）

- 不可對資料庫執行任何 **DML**（INSERT/UPDATE/DELETE）或 **DCL**（GRANT/REVOKE）。
- Schema 探勘只能用唯讀查詢：`INFORMATION_SCHEMA.*`、`sys.foreign_keys`、
  `sys.foreign_key_columns`、`OBJECT_DEFINITION()`。
- 產生的補強腳本（`add_missing_foreign_keys.sql`）是文件產出物，**不要拿去執行**。
