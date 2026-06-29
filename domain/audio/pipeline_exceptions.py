"""Audio pipeline exceptions."""


class AudioPipelineError(Exception):
    """Base exception for audio pipeline operations."""


class AudioValidationError(AudioPipelineError):
    """Raised when audio file validation fails."""


class AudioNormalizationError(AudioPipelineError):
    """Raised when loudness normalization fails."""


class AudioConcatenationError(AudioPipelineError):
    """Raised when audio concatenation fails."""


class AudioExportError(AudioPipelineError):
    """Raised when audio export fails."""


class FFmpegExecutionError(AudioPipelineError):
    """Raised when FFmpeg or FFprobe execution fails."""


class MissingAudioAssetError(AudioPipelineError):
    """Raised when required segment audio assets are missing."""
