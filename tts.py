import os
import uuid
from elevenlabs.client import ElevenLabs

# 🔑 HARD-CODE API KEY (OK for testing)
ELEVENLABS_API_KEY = "sk_e4d0f13c3df78927cd7e09dddcfc044bb1d9575526ef63e0"

# 🎙 Female, natural voice (Bella)
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

class ElevenLabsTTSService:
    def __init__(self):
        self.client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    def generate_voice(self, text: str, output_dir: str = None) -> str:
        if output_dir is None:
            output_dir = os.getcwd()

        print("🎙 Generating ElevenLabs voice...")

        audio_generator = self.client.text_to_speech.convert(
            voice_id=VOICE_ID,
            model_id="eleven_multilingual_v2",
            text=text,
        )

        output_path = os.path.join(
            output_dir,
            f"voice_{uuid.uuid4().hex}.mp3"
        )

        # 🔹 Save streamed audio properly
        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)

        print(f"✅ Voice generated → {output_path}")
        return output_path


# ============================
# TEST
# ============================
if __name__ == "__main__":
    tts = ElevenLabsTTSService()

    test_text = (
        "Welcome to paradise  salon. Mr sohail pathan , here you get luxury facility , and we will take care of you very good , first what would you like to have , russian or indian "
    )

    tts.generate_voice(test_text)
