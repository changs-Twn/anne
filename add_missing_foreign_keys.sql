/* =============================================================================
   add_missing_foreign_keys.sql
   Database : biz_anne  (server 163.17.141.61,8082)
   Purpose  : Document every relationship inferred by reading the schema, and
              generate the DDL that WOULD be needed for any relationship that
              is not currently enforced by a real FOREIGN KEY constraint.

   THIS SCRIPT IS NOT EXECUTED. Per task constraint, no DML/DCL (and, out of
   caution, no DDL either) was run against the live database. It is a
   generated artifact only, produced by reading INFORMATION_SCHEMA / sys.*
   catalog views (read-only) and the three view definitions.
   =============================================================================
*/

-- -----------------------------------------------------------------------------
-- 1. FINDING: every base-table relationship already has an explicit FK.
--    Inspected via sys.foreign_keys / sys.foreign_key_columns. All 7 columns
--    that look like foreign keys (by name + matching a PK elsewhere) already
--    carry a declared constraint. Nothing to add here.
-- -----------------------------------------------------------------------------
--   InboundHeader.EmployeeId      -> Employee.EmployeeId      (FK_InboundHeader_Employee)
--   OutboundHeader.EmployeeId     -> Employee.EmployeeId      (FK_OutboundHeader_Employee)
--   InboundDetail.InboundId       -> InboundHeader.InboundId  (FK_InboundDetail_InboundHeader)
--   InboundDetail.ProductId       -> Product.ProductId        (FK_InboundDetail_Product)
--   OutboundDetail.OutboundId     -> OutboundHeader.OutboundId(FK_OutboundDetail_OutboundHeader)
--   OutboundDetail.ProductId      -> Product.ProductId        (FK_OutboundDetail_Product)
--   InventoryDailyClosing.ProductId -> Product.ProductId      (FK_InventoryDailyClosing_Product)
--
-- No ALTER TABLE ... ADD CONSTRAINT statements are needed for base tables.


-- -----------------------------------------------------------------------------
-- 2. FINDING: the 3 reporting views have NO foreign keys, because SQL Server
--    views cannot carry FOREIGN KEY constraints at all (a structural
--    limitation, not an oversight). Each view's SELECT was read to infer the
--    relationship it implies:
--
--      v_InoutHeader   (UNION of InboundHeader + OutboundHeader)
--          .EmployeeId  -->  Employee.EmployeeId   (implied, unenforceable)
--
--      v_InoutDetail   (UNION of InboundDetail + OutboundDetail)
--          .ProductId   -->  Product.ProductId     (implied, unenforceable)
--
--      v_InventoryDailyClosing (JOIN InventoryDailyClosing + Product)
--          .ProductId   -->  Product.ProductId     (implied; already enforced
--                             on the underlying InventoryDailyClosing table,
--                             the view merely surfaces it)
--
--    Since "ALTER VIEW ... ADD CONSTRAINT" is not valid T-SQL, the closest
--    honest equivalent is to record the relationship as catalog metadata
--    (MS_ForeignKeyHint extended properties) so tooling / diagram generators
--    can still discover it. This is metadata documentation, not a real
--    constraint, and (like everything in this file) is NOT executed.
-- -----------------------------------------------------------------------------

EXEC sys.sp_addextendedproperty
    @name = N'MS_ForeignKeyHint',
    @value = N'References Employee.EmployeeId (view cannot enforce FK)',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'VIEW',   @level1name = N'v_InoutHeader',
    @level2type = N'COLUMN', @level2name = N'EmployeeId';

EXEC sys.sp_addextendedproperty
    @name = N'MS_ForeignKeyHint',
    @value = N'References Product.ProductId (view cannot enforce FK)',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'VIEW',   @level1name = N'v_InoutDetail',
    @level2type = N'COLUMN', @level2name = N'ProductId';

EXEC sys.sp_addextendedproperty
    @name = N'MS_ForeignKeyHint',
    @value = N'References Product.ProductId (view cannot enforce FK)',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'VIEW',   @level1name = N'v_InventoryDailyClosing',
    @level2type = N'COLUMN', @level2name = N'ProductId';

-- =============================================================================
-- END OF SCRIPT. Nothing above has been run against the database.
-- =============================================================================
