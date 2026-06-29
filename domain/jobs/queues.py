"""Job queue name constants."""

QUEUE_INGESTION = "ingestion"
QUEUE_LLM = "llm"
QUEUE_TTS = "tts"
QUEUE_AUDIO = "audio"
QUEUE_PUBLISHING = "publishing"
QUEUE_MONITORING = "monitoring"

ALL_QUEUES = (
    QUEUE_INGESTION,
    QUEUE_LLM,
    QUEUE_TTS,
    QUEUE_AUDIO,
    QUEUE_PUBLISHING,
    QUEUE_MONITORING,
)
