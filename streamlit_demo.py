# ui_streamlit/streamlit_app.py
import streamlit as st
import requests
from PIL import Image
from io import BytesIO

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI Video Ad Generator",
    page_icon="🎬",
    layout="wide"
)

# =========================
# BACKEND CONFIG
# =========================
try:
    API_HOST = st.secrets.get("BACKEND_URL") or "http://localhost:5000"
except Exception:
    API_HOST = "http://localhost:5000"

API_BASE = API_HOST.rstrip("/") + "/api/campaign"

# =========================
# HELPERS
# =========================
def safe_get_image(url, timeout=6):
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return Image.open(BytesIO(r.content))
    except Exception:
        return None


def post_generate_beauty(business_type, theme, num_scenes):
    return requests.post(
        f"{API_BASE}/generate_beauty_campaign",
        params={
            "business_type": business_type,
            "campaign_theme": theme,
            "num_scenes": num_scenes
        },
        timeout=900
    )


def post_generate_videos(
    campaign_id,
    scene_images,
    character_reference_url,
    business_name=None,
    phone=None,
    website=None,
):
    payload = {
        "scene_images": scene_images,
        "character_reference_url": character_reference_url,
        "business_name": business_name,
        "phone_number": phone,
        "website": website,
    }

    return requests.post(
        f"{API_BASE}/generate_campaign_videos/{campaign_id}",
        json=payload,
        timeout=1800
    )

# =========================
# HEADER
# =========================
st.markdown(
    "<h2 style='text-align:center;'>🎬 AI Beauty Video Ad Generator</h2>",
    unsafe_allow_html=True
)
st.caption("Character → Images → Cinematic Video Ads (DB-Free)")

# =========================
# SIDEBAR CONTROLS
# =========================
with st.sidebar:
    st.markdown("### Campaign Settings")

    business_type = st.selectbox(
        "Business Type",
        ["nail salon", "hair salon", "spa"]
    )

    theme = st.selectbox(
        "Campaign Theme",
        [
            "Christmas",
            "Valentine's Day",
            "Summer",
            "New Year",
            "Mother's Day",
            "Spring",
            "Holiday Season"
        ]
    )

    num_scenes = st.slider(
        "Number of Scenes",
        min_value=1,
        max_value=5,
        value=2
    )

    st.markdown("---")

    business_name = st.text_input("Business Name (optional)")
    phone = st.text_input("Phone Number (optional)")
    website = st.text_input("Website (optional)")

# =========================
# SESSION STATE
# =========================
if "campaign_data" not in st.session_state:
    st.session_state.campaign_data = None
if "video_data" not in st.session_state:
    st.session_state.video_data = None

# =========================
# MAIN ACTIONS
# =========================
col1, col2 = st.columns([2, 1])

# ---------- GENERATE IMAGES ----------
with col1:
    st.subheader("1️⃣ Generate Images")

    if st.button("✨ Generate Campaign", type="primary"):
        st.session_state.campaign_data = None
        st.session_state.video_data = None

        resp = post_generate_beauty(business_type, theme, num_scenes)

        if resp.status_code != 200:
            st.error(resp.text)
        else:
            st.session_state.campaign_data = resp.json()
            st.success("Images generated successfully!")

# ---------- GENERATE VIDEOS ----------
with col2:
    st.subheader("2️⃣ Generate Videos")

    data = st.session_state.campaign_data

    if data:
        campaign_id = data["campaign_id"]
        st.code(campaign_id)

        if st.button("🎥 Generate Videos"):
            scene_images = [
                s["image"]
                for s in data["scenes"]
                if s.get("image")
            ]

            if not scene_images:
                st.error("No scene images available")
            else:
                resp = post_generate_videos(
                    campaign_id=campaign_id,
                    scene_images=scene_images,
                    character_reference_url=data["character_reference_url"],
                    business_name=business_name or None,
                    phone=phone or None,
                    website=website or None
                )

                if resp.status_code != 200:
                    st.error(resp.text)
                else:
                    st.session_state.video_data = resp.json()
                    st.success("Videos generated successfully!")
    else:
        st.info("Generate images first")

st.divider()

# =========================
# IMAGE PREVIEW
# =========================
if st.session_state.campaign_data:
    st.markdown("### 🖼️ Image Preview")

    for s in st.session_state.campaign_data["scenes"]:
        img = safe_get_image(s.get("image"))
        if img:
            st.image(img, caption=f"Scene {s['scene_number']}", use_column_width=True)

st.divider()

# =========================
# VIDEO PREVIEW
# =========================
if st.session_state.video_data:
    merged = st.session_state.video_data.get("final_merged_video")

    if merged:
        st.markdown("### 🎬 Final Video")
        st.video(merged)

        st.markdown(
            f"<a href='{merged}' target='_blank'>⬇️ Download Video</a>",
            unsafe_allow_html=True
        )

st.caption("© AI Video Ad Generator — DB-Free, EC2-Ready")
