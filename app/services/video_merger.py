import os
import tempfile
import subprocess
import requests
import shutil
from typing import List, Optional


class VideoMerger:
    """
    VideoMerger
    - Uses local temp files ONLY because FFmpeg requires them
    - Guarantees cleanup after processing
    - No database
    - No image persistence
    """

    # ==========================================================
    # 🧹 SAFE DELETE
    # ==========================================================
    def _safe_remove(self, path: Optional[str]):
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    # ==========================================================
    # ⏱ GET VIDEO DURATION
    # ==========================================================
    def get_video_duration(self, video_path: str) -> float:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ],
            capture_output=True,
            text=True
        )
        return float(result.stdout.strip())

    # ==========================================================
    # 🎙 FIT AUDIO TO VIDEO DURATION
    # ==========================================================
    def fit_audio_to_duration(self, audio_path: str, duration: float) -> str:
        temp_dir = tempfile.gettempdir()
        output = os.path.join(temp_dir, f"fit_{os.path.basename(audio_path)}")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-af", f"apad=pad_dur={duration}",
                "-t", str(duration),
                output
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return output

    # ==========================================================
    # ⬇️ DOWNLOAD VIDEO (URL → TEMP FILE)
    # ==========================================================
    def _download_video(self, source: str, index: int) -> str:
        temp_dir = tempfile.gettempdir()
        local_path = os.path.join(temp_dir, f"scene_{index}.mp4")

        if source.startswith("http://") or source.startswith("https://"):
            r = requests.get(source, stream=True, timeout=30)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        else:
            if not os.path.exists(source):
                raise FileNotFoundError(source)
            shutil.copy(source, local_path)

        return local_path

    # ==========================================================
    # 🔇 REMOVE ORIGINAL AUDIO
    # ==========================================================
    def strip_audio(self, input_video: str) -> str:
        output = os.path.join(
            tempfile.gettempdir(),
            f"silent_{os.path.basename(input_video)}"
        )

        subprocess.run(
            ["ffmpeg", "-y", "-i", input_video, "-map", "0:v", "-c:v", "copy", "-an", output],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return output

    # ==========================================================
    # 🔊 ADD VOICE (OPTIONAL MUSIC)
    # ==========================================================
    def add_voice_and_music(
        self,
        silent_video: str,
        voice_path: str,
        music_path: Optional[str],
        music_volume: float = 0.2
    ) -> str:

        output = os.path.join(
            tempfile.gettempdir(),
            f"vo_{os.path.basename(silent_video)}"
        )

        if music_path:
            filter_complex = (
                f"[1:a]volume=1.0[a1];"
                f"[2:a]volume={music_volume}[a2];"
                f"[a1][a2]amix=inputs=2:duration=shortest[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", silent_video,
                "-i", voice_path,
                "-i", music_path,
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[a]",
                "-c:v", "copy",
                "-c:a", "aac",
                output
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-i", silent_video,
                "-i", voice_path,
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                output
            ]

        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output

    # ==========================================================
    # 🎞 APPLY FADE
    # ==========================================================
    def _fade_video(self, input_path: str, output_path: str, fade_in: bool, fade_out: bool, duration=0.7):
        total_dur = self.get_video_duration(input_path)

        vf, af = [], []
        if fade_in:
            vf.append(f"fade=t=in:st=0:d={duration}")
            af.append(f"afade=t=in:st=0:d={duration}")
        if fade_out:
            vf.append(f"fade=t=out:st={total_dur-duration}:d={duration}")
            af.append(f"afade=t=out:st={total_dur-duration}:d={duration}")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vf", ",".join(vf) if vf else "null",
                "-af", ",".join(af) if af else "anull",
                output_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    # ==========================================================
    # 🎬 MERGE ALL SCENES
    # ==========================================================
    def merge_videos(self, video_paths: List[str], campaign_id: str, output_name: str) -> str:
        temp_dir = tempfile.gettempdir()
        processed = []

        for i, p in enumerate(video_paths):
            out = os.path.join(temp_dir, f"fade_{i}.mp4")
            self._fade_video(p, out, i != 0, i != len(video_paths)-1)
            processed.append(out)

        concat_file = os.path.join(temp_dir, f"concat_{campaign_id}.txt")
        with open(concat_file, "w") as f:
            for p in processed:
                f.write(f"file '{p}'\n")

        output = os.path.join(temp_dir, f"{campaign_id}_{output_name}")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c:v", "libx264", "-c:a", "aac", output],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # cleanup intermediate fade files + concat file
        for p in processed:
            self._safe_remove(p)
        self._safe_remove(concat_file)

        return output

    # ==========================================================
    # 🚀 FULL PIPELINE (AUTO CLEANUP)
    # ==========================================================
    def process_full_pipeline(
        self,
        scene_video_urls: List[str],
        voice_paths: List[str],
        campaign_id: str,
        output_name: str,
        background_music: Optional[str] = None
    ) -> str:

        temp_files = []
        voiced_scenes = []

        try:
            for i, url in enumerate(scene_video_urls):
                video = self._download_video(url, i)
                temp_files.append(video)

                duration = self.get_video_duration(video)
                fitted_voice = self.fit_audio_to_duration(voice_paths[i], duration)
                temp_files.append(fitted_voice)

                silent = self.strip_audio(video)
                temp_files.append(silent)

                voiced = self.add_voice_and_music(
                    silent_video=silent,
                    voice_path=fitted_voice,
                    music_path=None
                )
                voiced_scenes.append(voiced)
                temp_files.append(voiced)

            merged = self.merge_videos(voiced_scenes, campaign_id, output_name)
            return merged

        finally:
            # 🔥 GUARANTEED CLEANUP
            for f in temp_files:
                self._safe_remove(f)


# Singleton instance
video_merger = VideoMerger()
