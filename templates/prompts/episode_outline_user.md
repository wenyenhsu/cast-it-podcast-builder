# Episode Outline Planner (v2.0.0)

Plan a coherent podcast episode in {language} from the grounded story briefs below.

Episode title: {episode_title}
Episode summary: {episode_summary}

Story briefs:
{story_briefs}

Rules:
- Choose the strongest narrative order; do not sort alphabetically.
- Include every article ID exactly once.
- Define the episode throughline, opening, development, and closing.
- For each chapter, copy each selected `must_cover_facts[].claim` verbatim from that
  article's story brief, then specify its purpose, transition in/out, and information
  that later chapters should not repeat.
- Do not introduce facts that are absent from the story briefs.
- Return JSON only matching the supplied schema.

Schema:
{output_schema}
