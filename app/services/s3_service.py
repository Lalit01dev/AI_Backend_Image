import os
import boto3


def upload_to_s3(local_path: str) -> str:
    s3_bucket = os.getenv("S3_CAMPAIGN_BUCKET", "ai-images-2")
    s3_region = os.getenv("AWS_REGION")

    s3_client = boto3.client(
        "s3",
        region_name=s3_region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    filename = os.path.basename(local_path)
    key = f"campaigns/videos/{filename}"

    s3_client.upload_file(
        local_path,
        s3_bucket,
        key,
        ExtraArgs={"ContentType": "video/mp4"},
    )

    if s3_region:
        return f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{key}"
    return f"https://{s3_bucket}.s3.amazonaws.com/{key}"
