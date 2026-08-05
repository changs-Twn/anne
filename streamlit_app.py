import streamlit as st

from streamlit_common.config import bootstrap_db_env

st.set_page_config(page_title="Mini ERP", layout="wide")
bootstrap_db_env()

from streamlit_common import auth  # noqa: E402  (must follow bootstrap_db_env)
from streamlit_pages import employee, inbound, outbound, product, reports  # noqa: E402

auth.require_login()
auth.render_sidebar_user()
auth.render_password_prompt()

st.sidebar.warning(
    "⚠️ 此版本透過 pymssql/FreeTDS 連線（Streamlit Cloud 無法安裝 ODBC Driver 18）。"
    "中文欄位（物料/員工名稱）可能顯示亂碼，這是已知限制，非本次修改造成的資料損毀。",
    icon="⚠️",
)

pages = {
    "主數據": [
        st.Page(product.render, title="物料管理", url_path="product"),
        st.Page(employee.render, title="員工管理", url_path="employee"),
    ],
    "交易數據": [
        st.Page(inbound.render, title="入庫管理", url_path="inbound"),
        st.Page(outbound.render, title="出庫管理", url_path="outbound"),
    ],
    "報表查詢": [
        st.Page(reports.render_inout_header, title="入出單據", url_path="reports-inout-header"),
        st.Page(reports.render_inout_detail, title="入出明細", url_path="reports-inout-detail"),
        st.Page(reports.render_daily_closing, title="日結餘額表", url_path="reports-daily-closing"),
    ],
}

nav = st.navigation(pages)
nav.run()
