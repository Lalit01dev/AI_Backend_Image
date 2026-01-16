import os
import uuid
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()




class ElevenLabsTTSService:
    """
    ElevenLabs Text-to-Speech service
    Generates ultra-natural voiceovers (scene-wise)
    """

    def __init__(self):
        
        self.client = ElevenLabs(
            
            api_key=os.getenv("ELEVENLABS_API_KEY")
        )

        # Default natural female voice 
        self.voice_id = "EXAVITQu4vr4xnSDxMaL"

        print("ElevenLabs TTS Service initialized")

    
    def generate_voice(
        self,
        text: str,
        output_dir: str = None
    ) -> str:

        if not output_dir:
            output_dir = os.getenv("TEMP", "/tmp")

        output_path = os.path.join(
            output_dir,
            f"voice_{uuid.uuid4().hex}.mp3"
        )

        audio_stream = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )

        # IMPORTANT FIX: stream → bytes
        with open(output_path, "wb") as f:
            for chunk in audio_stream:
                if chunk:
                    f.write(chunk)

        return output_path



# Singleton
elevenlabs_tts_service = ElevenLabsTTSService()
