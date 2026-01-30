def build_scene_narration(scene_config, business_info):
    parts = []
    text = scene_config.get("text", {}) if scene_config else {}

    if text.get("headline"):
        parts.append(text["headline"])
    if text.get("subtext"):
        parts.append(text["subtext"])
    if text.get("cta"):
        parts.append(text["cta"])

    if business_info:
        if text.get("cta") and business_info.get("phone"):
            parts.append(f"Call us at {business_info['phone']}")
        if text.get("cta") and business_info.get("website"):
            parts.append(f"Visit {business_info['website']}")

    return ". ".join(parts)
