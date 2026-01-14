# streamlit_app.py
import streamlit as st
import requests
import time
import os
from dotenv import load_dotenv

# =========================================================
# ENV SETUP (LOCAL + CLOUD SAFE)
# =========================================================
load_dotenv()

BASE_URL = os.getenv("BACKEND_URL") or st.secrets.get("BACKEND_URL")
if not BASE_URL:
    st.error("❌ BACKEND_URL is not configured")
    st.stop()

# =========================================================
# STREAMLIT CONFIG
# =========================================================
st.set_page_config(
    page_title="AI Ad Studio",
    page_icon="🎬",
    layout="wide"
)

# =========================================================
# HELPERS
# =========================================================
def api_post(url, params=None, timeout=300):
    try:
        r = requests.post(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"__error__": "Backend request failed"}

def start_progress():
    bar = st.progress(0)
    text = st.empty()
    return bar, text

def update_progress(bar, text, percent, message):
    bar.progress(percent)
    text.markdown(f"**{message}**")

# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
    <div style="padding:20px;border-radius:14px;
    background:linear-gradient(90deg,#0f2027,#203a43,#2c5364);
    color:white">
        <h1 style="margin-bottom:0">🎬 AI Ad Studio</h1>
        <p style="margin-top:6px;font-size:16px">
            Generate professional AI video ads using Veo 3.1
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# SIDEBAR — USER CAN CHOOSE SCENES
# =========================================================
st.sidebar.header("⚙️ Campaign Settings")

business_type = st.sidebar.selectbox(
    "Business type",
    ["nail salon", "hair salon", "spa"]
)

campaign_theme = st.sidebar.selectbox(
    "Theme",
    ["Christmas", "Valentine", "New Year", "Summer", "Spring"]
)

num_scenes = st.sidebar.selectbox(
    "Number of scenes",
    [1, 2, 3],
    index=2
)

st.sidebar.caption("ℹ️ Recommended: 3 scenes for best results")

character_age = st.sidebar.text_input("Character age", "28-32")
character_gender = st.sidebar.selectbox("Gender", ["woman", "man", "non-binary"])
character_ethnicity = st.sidebar.text_input("Ethnicity", "Indian")

st.sidebar.divider()
st.sidebar.subheader("📞 Business Info")

business_name = st.sidebar.text_input("Business name", "Paradise Nails")
phone_number = st.sidebar.text_input("Phone", "9876543210")
website = st.sidebar.text_input("Website", "https://example.com")

# =========================================================
# STEP 1 — GENERATE IMAGES
# =========================================================
st.markdown("## 🖼️ Step 1 — Generate Campaign Images")

if st.button("✨ Generate Campaign Images"):
    with st.spinner("Generating images..."):
        params = {
            "business_type": business_type,
            "campaign_theme": campaign_theme,
            "character_age": character_age,
            "character_gender": character_gender,
            "character_ethnicity": character_ethnicity,
            "num_scenes": num_scenes
        }

        res = api_post(
            f"{BASE_URL}/api/campaign/generate_beauty_campaign",
            params=params,
            timeout=600
        )

    if "__error__" in res:
        st.error("❌ Image generation failed")
        st.stop()

    st.success("✅ Images generated successfully")
    st.session_state["campaign"] = res
    st.session_state["campaign_id"] = res["campaign_id"]

# =========================================================
# SHOW GENERATED IMAGES
# =========================================================
campaign = st.session_state.get("campaign")
if campaign:
    st.markdown("### 🖼️ Generated Images")
    cols = st.columns(len(campaign["scenes"]))

    for idx, scene in enumerate(campaign["scenes"]):
        with cols[idx]:
            st.image(scene["image"], use_column_width=True)
            st.caption(f"Scene {scene['scene_number']}")

# =========================================================
# STEP 2 — GENERATE VIDEO
# =========================================================
st.markdown("## 🎥 Step 2 — Generate Final Video")

campaign_id = st.text_input(
    "Campaign ID",
    value=st.session_state.get("campaign_id", "")
)

if "is_generating" not in st.session_state:
    st.session_state["is_generating"] = False

if st.button(
    "🎬 Generate Video",
    disabled=st.session_state["is_generating"]
):
    if not campaign_id:
        st.error("Campaign ID is required")
        st.stop()

    st.session_state["is_generating"] = True
    st.session_state.pop("video_result", None)

    bar, text = start_progress()

    try:
        update_progress(bar, text, 10, "🚀 Starting video generation")

        params = {
            "business_name": business_name,
            "phone_number": phone_number,
            "website": website
        }

        update_progress(bar, text, 25, "📡 Contacting backend")

        res = api_post(
            f"{BASE_URL}/api/campaign/generate_campaign_videos/{campaign_id}",
            params=params,
            timeout=3600
        )

        if "__error__" in res:
            raise Exception("Video generation failed")

        update_progress(bar, text, 85, "🎞️ Processing final video")

        st.session_state["video_result"] = res

        update_progress(bar, text, 100, "✅ Video ready")

        time.sleep(0.3)
        bar.empty()
        text.empty()

        st.success("🎉 Final video generated")

    except Exception:
        bar.empty()
        text.empty()
        st.error("❌ Video generation failed")

    finally:
        st.session_state["is_generating"] = False

# =========================================================
# DISPLAY FINAL VIDEO
# =========================================================
video_result = st.session_state.get("video_result")

if video_result:
    final_video = (
        video_result.get("final_merged_video")
        or video_result.get("final_video")
    )

    if final_video:
        st.markdown("## 🚀 Final AI Advertisement")
        st.video(final_video)

        try:
            r = requests.get(final_video)
            if r.status_code == 200:
                st.download_button(
                    "⬇️ Download Final Ad",
                    data=r.content,
                    file_name="final_ai_ad.mp4",
                    mime="video/mp4"
                )
        except Exception:
            pass

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("⚡ AI Ad Studio — Powered by Veo 3.1")
