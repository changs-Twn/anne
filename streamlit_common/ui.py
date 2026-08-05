import streamlit as st


def confirm_delete_button(key, label="刪除"):
    """Two-click delete confirmation. Returns True exactly once, on the confirming click."""
    armed_key = f"_confirm_armed_{key}"

    if not st.session_state.get(armed_key, False):
        if st.button(label, key=f"_btn_{key}"):
            st.session_state[armed_key] = True
            st.rerun()
        return False

    st.warning("確定要刪除嗎？此操作無法復原。")
    col1, col2 = st.columns(2)
    confirmed = col1.button("確認刪除", key=f"_btn_confirm_{key}", type="primary")
    cancelled = col2.button("取消", key=f"_btn_cancel_{key}")

    if cancelled:
        st.session_state[armed_key] = False
        st.rerun()
    if confirmed:
        st.session_state[armed_key] = False
        return True
    return False
