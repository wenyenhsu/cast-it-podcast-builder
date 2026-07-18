# Podcast Chapter Rewrite (v2.0.0)

Rewrite this podcast chapter in {language} using the critic's concrete instructions.

Story brief:
{story_brief}

Outline chapter:
{outline_chapter}

Source article:
<<<ARTICLE_START>>>
{source_content}
<<<ARTICLE_END>>>

{rag_context_block}

Previous chapter summary: {previous_chapter_summary}
Previous final lines: {previous_chapter_last_lines}
Next transition hook: {next_transition_hook}
Already covered: {already_covered}

Original chapter:
{chapter}

Critic:
{critic}

Remove unsupported claims, restore missing facts, reduce repetition, and make the
conversation natural. Do not introduce new facts. Return the normal podcast script JSON.

Schema:
{output_schema}
