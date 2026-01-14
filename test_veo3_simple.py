import time
import base64
import mimetypes
import os
from google import genai
from google.genai.types import Blob, Part

# Load API key from environment variable
api_key = os.environ.get('GOOGLE_API_KEY')
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it with your Google AI API key.")

client = genai.Client(api_key=api_key)

prompt = "women smiling and walking in a park during autumn, cinematic, 4k resolution"

filename = "C:\Users\Administrator\Desktop\commercial-video-generator\test_character.png"  # or .jpg

# Read Image
with open(filename, "rb") as f:
    img_bytes = f.read()

# Guess MIME TYPE
mime = mimetypes.guess_type(filename)[0]  # "image/png" or "image/jpeg"

# Create EXACT SAME STRUCTURE as image.parts[0].as_image()
user_image = Part(
    inline_data=Blob(
        data=img_bytes,
        mime_type=mime
    )
)

# Generate video with Veo using your image
operation = client.models.generate_videos(
    model="veo-3.1-generate-preview",
    prompt=prompt,
    image=user_image.as_image(),   # IMPORTANT!!!
)

# Poll
while not operation.done:
    print("Waiting...")
    time.sleep(10)
    operation = client.operations.get(operation)

# Download video
video = operation.response.generated_videos[0]
client.files.download(file=video.video)
# client.files.download(
#     name=video.video.uri,
#     output_file_name="video_output.mp4"
# )
video.video.save("video_output.mp4")
print("Video saved as video_output.mp4")

print("Video saved as video_output.mp4")