---
name: reverse-engineer-er-diagram
description: Reverse-engineer a complete Entity-Relationship Diagram from a live SQL Server database using only read-only schema introspection (no DML/DCL, no data touched), distinguishing relationships enforced by real FOREIGN KEY constraints from relationships that are only implied (e.g. through a view's UNION/JOIN) and cannot be formally enforced. Produces a self-contained HTML diagram plus a generated-not-executed remediation script.
---

# Reverse-engineer an ER Diagram (read-only)

用在：拿到一個資料庫連線，要畫出完整 ER 圖，但**不准跑任何 DML/DCL**（甚至不該跑 DDL），
而且資料表之間的關聯只有「部分」有寫 `FOREIGN KEY`，其餘要自己讀 schema 判斷。

## 為什麼需要這份 skill

`sys.foreign_keys` 只會告訴你「資料表上」宣告過的 FK。它不會告訴你：

1. 一個看起來像外鍵的欄位（例如 `EmployeeId`）是不是**故意**沒有 FK（schema 設計者忘了寫，
   或刻意不強制），還是根本沒有對應的來源表。
2. Views／報表用的衍生物件對基底表的引用——這些**在關聯式資料庫裡結構上就不能有 FK**，
   但畫 ER 圖的時候仍然是「關聯」，只是「未強制」。

分不清這兩種「沒有 FK」，畫出來的 ER 圖要嘛漏掉關聯，要嘛會亂生出一堆其實不該加的
`ALTER TABLE ADD CONSTRAINT`。

## 步驟

### 1. 列出所有物件（含 view）

```sql
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES;
```

不要只看 `BASE TABLE`——`VIEW` 常常藏著额外的隱含關聯（見步驟 5）。

### 2. 抓每個資料表的欄位、型別、PK

```sql
SELECT c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.CHARACTER_MAXIMUM_LENGTH, c.IS_NULLABLE,
       COLUMNPROPERTY(OBJECT_ID(c.TABLE_SCHEMA+'.'+c.TABLE_NAME), c.COLUMN_NAME, 'IsIdentity')
FROM INFORMATION_SCHEMA.COLUMNS c ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;

SELECT tc.TABLE_NAME, ku.COLUMN_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY';
```

### 3. 抓所有「已經寫」的 FK（涵蓋全部資料表，不要只挑幾張）

```sql
SELECT OBJECT_NAME(fk.parent_object_id) AS FromTable, c1.name AS FromColumn,
       OBJECT_NAME(fk.referenced_object_id) AS ToTable, c2.name AS ToColumn, fk.name
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
JOIN sys.columns c1 ON fkc.parent_object_id = c1.object_id AND fkc.parent_column_id = c1.column_id
JOIN sys.columns c2 ON fkc.referenced_object_id = c2.object_id AND fkc.referenced_column_id = c2.column_id;
```

### 4. 找「看起來像 FK 但沒宣告」的欄位

對每一張表，找出欄位名稱符合「`<X>Id`」且能對到另一張表 PK 欄位名稱的欄位
（例如 `ProductId` 對到 `Product.ProductId`），但步驟 3 的結果裡沒有涵蓋。這些才是真正
「缺 FK」的候選——**只有這些**才需要生成 `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` 腳本。

不要看到欄位名稱像 FK 就直接假設一定缺東西——先跟步驟 3 的結果比對過。

### 5. 讀 view 定義，找隱含關聯

```sql
SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.SomeView'));
```

Views 不能有 FK（T-SQL 沒有 `ALTER VIEW ... ADD CONSTRAINT` 這種語法）。如果 view 的
`SELECT`／`UNION`／`JOIN` 用到某欄位去對應另一張表的 PK，那是「隱含關聯」——在 ER 圖上要畫出來，
但要用不同的視覺樣式（例如虛線）標示「未強制」，不要跟步驟 3 的真 FK 混在一起。

### 6. 產生腳本，但不要執行

把步驟 4（真的缺 FK）跟步驟 5（view 隱含、structurally 不能加 FK）分開寫成一份 `.sql` 檔：

- 步驟 4 的缺口 → 寫 `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY ...`。
- 步驟 5 的隱含關聯 → FK 語法不適用；改用 `sp_addextendedproperty` 之類的 metadata 註記，
  或純粹寫成註解說明「view 無法加 FK，關聯只存在於定義裡」。

檔案開頭清楚寫「本腳本未執行」，並在對話裡明講「沒有對資料庫下任何 DML/DCL/DDL」。

### 7. 畫 ER 圖

用一張 self-contained 的 HTML（inline SVG，不用外部函式庫）：

- 每張表一個框，欄位列出，PK/FK 用小標籤標出。
- 真 FK 關聯：實線箭頭 + 基數標籤（如 `1─N`）。
- 隱含（view）關聯：另一種顏色的虛線箭頭，並附一個 Legend 說明兩種線的差異。
- 圖表下方附一張「關聯總表」（From / Column / To / Column / Enforced? / Constraint 或原因），
  讓人一眼看出哪些是真的、哪些是推的。

## 常見誤區

- **不要**因為任務說「有些沒寫 FK」就預設一定要生出 ALTER TABLE 腳本——先老實查一遍，
  如果資料表關聯其實全部都有 FK（缺口只在 view），就照實講，不要硬湊假的缺口。
- **不要**把「view 沒有 FK」跟「資料表忘記寫 FK」用同一種視覺樣式畫出來，這是兩種性質不同的「沒有」。
- 讀取中文欄位時注意用戶端編碼（見專案 `CLAUDE.md`「已知坑」一節），亂碼不代表資料本身壞掉，
  下結論前要先排除顯示層問題。
