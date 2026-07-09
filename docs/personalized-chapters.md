# Personalized Chapter Feeds

Every listener gets their own daily podcast — assembled from shared building
blocks, not generated per user.

## How it works

```
Daily pipeline (fixed cost, once):          Per listener (nearly free):
──────────────────────────────────         ────────────────────────────
import articles from all sources           personal_chapters() ranks the
score/tag/cluster, pick top 8              chapter pool by the listener's
one script CHAPTER per article             tag affinity (listening history
one MP3 per chapter + full episode         + declared interests)
publish chapters to Supabase                        ↓
                                           frontend plays top N chapters
                                           as a seamless queue
```

- The **full episode** (`episodes` table) still exists — it is the generic
  "everything" edition.
- **Chapters** (`chapters` table) are per-article MP3s cut from the same
  audio. A listener's personal feed is the subset of today's chapters that
  matches their interests.

## Backend pieces (this repo)

| Piece | Where |
|---|---|
| Segment → article link | `ScriptSegment.article` (set by chaptered generation) |
| Chapter MP3 build | `services/audio/pipeline/chapters.py`, runs automatically at the end of the audio pipeline |
| Chapter asset rows | `AudioAsset` with `article` set, `script_segment` null, not final |
| Supabase publish | `SupabasePublisher._replace_chapters` — uploads MP3s, replaces `chapters` + `chapter_tags` rows per episode |
| Schema | `supabase/migrations/20260709000001_chapters.sql` |

## Frontend contract (cast-it-frontend)

### Get a listener's daily lineup

```js
const { data: lineup } = await supabase.rpc("personal_chapters", {
  p_session_id: sessionId,   // anonymous session id, same as personal_feed
  p_limit: 5,                // chapters per daily lineup
  p_days: 3,                 // how far back the pool reaches
});
```

Returns rows from `chapters`, best-match first:

| column | meaning |
|---|---|
| `id` | chapter id (uuid) |
| `episode_id` | source episode |
| `article_id` | source article |
| `position` | order within the source episode |
| `title` / `summary` / `category` | from the source article |
| `duration_seconds` | chapter length |
| `audio_url` | public MP3 URL (streamable, range requests OK) |
| `published_at` | when the chapter was built |

Scoring mirrors `personal_feed` v3: time-decayed listening activity per tag
(7-day half-life) plus the declared-interest prior for logged-in users.
Anonymous sessions work via `p_session_id`.

### Playback

Play the returned rows in order as a queue — no stitching required. Gapless
or ~0.5 s crossfade between chapters sounds natural since every chapter is
loudness-normalized to the same LUFS target.

### Activity events

Keep logging `activity_events` with the **episode_id of the chapter's
source episode** (`chapter.episode_id`) so listening feeds tag affinity via
the existing `episode_tags` join. (A future migration can add chapter-level
event granularity.)

### Tags for a chapter

```js
const { data } = await supabase
  .from("chapter_tags")
  .select("tag_slug, tags(name)")
  .eq("chapter_id", chapterId);
```

## Ops notes

- Chapter build adds a few minutes of FFmpeg CPU per day; TTS cost is
  unchanged (chapters reuse the same segment audio as the full episode).
- Re-publishing an episode replaces its chapters wholesale (new ids), so the
  frontend should treat chapter ids as ephemeral and key UI state by
  `article_id` or `episode_id + position`.
- Daily pool size: `MAX_EPISODE_ARTICLES` (currently 8) in
  `domain/intelligence/constants.py`.
