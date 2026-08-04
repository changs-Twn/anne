MENU = [
    {
        "title": "主數據",
        "children": [
            {"title": "物料管理", "endpoint": "product.list_view"},
            {"title": "員工管理", "endpoint": "employee.list_view"},
        ],
    },
    {
        "title": "交易數據",
        "children": [
            {"title": "入庫管理", "endpoint": "inbound.list_view"},
            {"title": "出庫管理", "endpoint": "outbound.list_view"},
        ],
    },
    {
        "title": "報表查詢",
        "children": [
            {"title": "入出單據", "endpoint": "reports.inout_header"},
            {"title": "入出明細", "endpoint": "reports.inout_detail"},
            {"title": "日結餘額表", "endpoint": "reports.daily_closing"},
        ],
    },
]
