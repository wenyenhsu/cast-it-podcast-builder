# Whole-Episode Coherence Pass (v2.0.0)

Polish this complete podcast script in {language} for cross-chapter flow.

Outline:
{episode_outline}

Grounded story briefs:
{story_briefs}

Script:
{script}

Rules:
- Preserve every `segment_index` exactly once and in ascending order.
- Preserve the exact segment count and every segment's speaker/voice fields so downstream
  TTS chapter ownership remains stable.
- Improve callbacks, transitions, pacing, and remove obvious repetition.
- Do not add or materially change factual claims.
- Keep short natural turns and avoid mechanical Q&A.
- Return podcast script JSON matching the supplied coherence schema only.

Schema:
{output_schema}
