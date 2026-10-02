from datetime import timezone

import streamlit as st

from status_probe import MIN_REQUEST_INTERVAL_SECONDS, check_scraps_status

st.set_page_config(page_title="Scraps Down Detector", page_icon="🔍")

st.markdown(
    """
    <style>
    .status-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 24px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Scraps Down Detector")
st.write("Status checks for scraps.hackclub.com")

st.sidebar.header("Settings")
refresh_rate = st.sidebar.slider(
    "Refresh rate (seconds)",
    min_value=MIN_REQUEST_INTERVAL_SECONDS,
    max_value=300,
    value=MIN_REQUEST_INTERVAL_SECONDS,
    step=30,
    help="Checks are shared across sessions and never run more often than once per minute per server process.",
)


@st.fragment(run_every=refresh_rate)
def render_status():
    status = check_scraps_status()
    status_code = status.status_code

    if status_code == 200:
        st.success("Scraps is online ✅")
        st.metric(label="Status code", value=status_code, delta="Healthy")

        if st.button("Celebrate Scraps actually working (rare event)"):
            st.balloons()
    elif status_code is not None:
        st.error("Scraps returned an unexpected response")
        st.metric(
            label="Status code",
            value=status_code,
            delta="Issues detected",
            delta_color="inverse",
        )
    else:
        st.error("Scraps is down or unreachable")
        st.metric(label="Status code", value="OFFLINE", delta="Check failed", delta_color="inverse")

        if status.error == "timeout":
            st.caption("The status check timed out after 5 seconds.")
        elif status.error == "request":
            st.caption("The detector could not connect to Scraps.")
        else:
            st.caption("The detector hit an unexpected error. Try again after the next check interval.")

    st.divider()
    st.subheader("Activity log")
    checked_at = status.checked_at.astimezone(timezone.utc).strftime("%H:%M:%S UTC")
    st.write(f"Last checked at: {checked_at}")


render_status()
