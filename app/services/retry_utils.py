import asyncio


async def generate_video_with_retries(
    generator,
    *,
    scene_image_url,
    motion_prompt,
    text_overlays,
    campaign_id,
    scene_number,
    business_info,
    product_type="beauty",
    retries=3,
    base_delay=8,
):
    last_exc = None

    for attempt in range(1, retries + 1):
        try:
            return await generator.generate_video_with_text(
                scene_image_url=scene_image_url,
                motion_prompt=motion_prompt,
                text_overlays=text_overlays,
                campaign_id=campaign_id,
                scene_number=scene_number,
                business_info=business_info,
                product_type=product_type,
            )

        except Exception as e:
            last_exc = e
            msg = str(e).lower()

            if (
                "429" in msg
                or "resource_exhausted" in msg
                or "timeout" in msg
                or "temporar" in msg
                or "no videos generated" in msg
            ):
                if attempt < retries:
                    wait = base_delay * (2 ** (attempt - 1))
                    print(f"Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue

            raise

    raise last_exc
