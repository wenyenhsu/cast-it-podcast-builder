"""FFmpeg argument builders for the audio pipeline.

Every builder returns the argument list without the binary itself —
``FFmpegRunner`` prepends the configured ffmpeg binary.
"""

from pathlib import Path

# Segments arrive from TTS providers at varying rates (Chatterbox emits
# 24 kHz) while silence gaps are generated at the pipeline default of
# 44.1 kHz. Normalization resamples every segment to this common rate so
# the concat demuxer receives uniform inputs.
PIPELINE_SAMPLE_RATE = 44100


class FFmpegCommands:
    """Static builders for the FFmpeg invocations used by the pipeline."""

    @staticmethod
    def generate_silence(
        output_path: Path,
        *,
        duration_seconds: float,
        sample_rate: int,
    ) -> list[str]:
        return [
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={sample_rate}:cl=mono",
            "-t",
            f"{duration_seconds}",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

    @staticmethod
    def loudnorm(
        input_path: Path,
        output_path: Path,
        *,
        target_lufs: float,
        sample_rate: int = PIPELINE_SAMPLE_RATE,
    ) -> list[str]:
        return [
            "-y",
            "-i",
            str(input_path),
            "-af",
            f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

    @staticmethod
    def concat_demuxer(list_path: Path, output_path: Path) -> list[str]:
        return [
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

    @staticmethod
    def mix_background_music(
        speech_path: Path,
        music_path: Path,
        output_path: Path,
        *,
        music_volume: float,
        fade_in_seconds: float,
        fade_out_seconds: float,
    ) -> list[str]:
        music_chain = (
            f"[1:a]volume={music_volume},"
            f"afade=t=in:st=0:d={fade_in_seconds}[music]"
        )
        mix_chain = (
            "[0:a][music]amix=inputs=2:duration=first:dropout_transition="
            f"{fade_out_seconds}[out]"
        )
        return [
            "-y",
            "-i",
            str(speech_path),
            "-stream_loop",
            "-1",
            "-i",
            str(music_path),
            "-filter_complex",
            f"{music_chain};{mix_chain}",
            "-map",
            "[out]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

    @staticmethod
    def export_mp3(
        input_path: Path,
        output_path: Path,
        *,
        bitrate: int,
        sample_rate: int,
    ) -> list[str]:
        return [
            "-y",
            "-i",
            str(input_path),
            "-ar",
            str(sample_rate),
            "-c:a",
            "libmp3lame",
            "-b:a",
            f"{bitrate}k",
            str(output_path),
        ]
