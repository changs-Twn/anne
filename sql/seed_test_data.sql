-- ============================================================================
-- Mini ERP 補充測試資料 (biz_anne)
-- 可重複執行 (每筆 INSERT 前都有 IF NOT EXISTS 判斷)，不會刪除或覆蓋現有資料。
-- 目的：補一批「有明細/無明細」都存在的 Product、Employee，方便測試
--       主檔刪除保護（有明細擋刪除、無明細可刪除）。
-- ============================================================================

USE biz_anne;
GO

-- ----------------------------------------------------------------------------
-- 1. 物料：P031、P032 全新無明細（可刪除測試用）；P033 之後會被入庫單參照（刪除應被擋下）
-- ----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM Product WHERE ProductId = 'P031')
    INSERT INTO Product (ProductId, ProductName, StockBalance) VALUES ('P031', '測試物料-無明細A', 0);

IF NOT EXISTS (SELECT 1 FROM Product WHERE ProductId = 'P032')
    INSERT INTO Product (ProductId, ProductName, StockBalance) VALUES ('P032', '測試物料-無明細B', 0);

IF NOT EXISTS (SELECT 1 FROM Product WHERE ProductId = 'P033')
    INSERT INTO Product (ProductId, ProductName, StockBalance) VALUES ('P033', '測試物料-有明細', 100);
GO

-- ----------------------------------------------------------------------------
-- 2. 員工：E019、E020 全新無單據（可刪除測試用）；E021 之後會被出庫單參照（刪除應被擋下）
-- ----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM Employee WHERE EmployeeId = 'E019')
    INSERT INTO Employee (EmployeeId, EmployeeName, Email) VALUES ('E019', '測試員工-無單據A', 'test19@minierp.local');

IF NOT EXISTS (SELECT 1 FROM Employee WHERE EmployeeId = 'E020')
    INSERT INTO Employee (EmployeeId, EmployeeName, Email) VALUES ('E020', '測試員工-無單據B', 'test20@minierp.local');

IF NOT EXISTS (SELECT 1 FROM Employee WHERE EmployeeId = 'E021')
    INSERT INTO Employee (EmployeeId, EmployeeName, Email) VALUES ('E021', '測試員工-有單據', 'test21@minierp.local');
GO

-- ----------------------------------------------------------------------------
-- 3. 入庫單：讓 P033 產生明細，之後刪除 P033 應該被擋下
-- ----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM InboundHeader WHERE InboundId = 'IN20260801901')
BEGIN
    INSERT INTO InboundHeader (InboundId, InboundDate, EmployeeId) VALUES ('IN20260801901', '2026-08-01', 'E001');
    INSERT INTO InboundDetail (InboundId, LineNum, ProductId, ProductName, Quantity)
    VALUES ('IN20260801901', 1, 'P033', '測試物料-有明細', 50);
END
GO

-- ----------------------------------------------------------------------------
-- 4. 出庫單：讓 E021 產生單據，之後刪除 E021 應該被擋下
-- ----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM OutboundHeader WHERE OutboundId = 'OUT20260801901')
BEGIN
    INSERT INTO OutboundHeader (OutboundId, OutboundDate, EmployeeId) VALUES ('OUT20260801901', '2026-08-01', 'E021');
    INSERT INTO OutboundDetail (OutboundId, LineNum, ProductId, ProductName, Quantity)
    VALUES ('OUT20260801901', 1, 'P033', '測試物料-有明細', 20);
END
GO

-- ----------------------------------------------------------------------------
-- 驗證查詢（可選，執行後人工確認）
-- ----------------------------------------------------------------------------
-- SELECT * FROM Product WHERE ProductId IN ('P031','P032','P033');
-- SELECT * FROM Employee WHERE EmployeeId IN ('E019','E020','E021');
-- SELECT * FROM v_InoutDetail WHERE ProductId = 'P033';
-- SELECT * FROM v_InoutHeader WHERE EmployeeId = 'E021';
