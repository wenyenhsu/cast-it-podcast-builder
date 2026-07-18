# Podcast Chapter Critic (v2.0.0)

Evaluate the chapter against its sources and editorial plan. Write the evaluation in
{language}, but preserve exact names and source wording where necessary.

Story brief:
{story_brief}

Outline chapter:
{outline_chapter}

Already covered before this chapter:
{already_covered}

Expected transition:
{expected_transition}

Generated chapter:
{chapter}

Check fact coverage, unsupported specifics, repetition, mechanical dialogue, supported
causality, internal flow, transitions, and language. A chapter with any unsupported
specific claim must fail. Set `language_matches` to false only when the chapter is
substantially written in the wrong language; wording, tone, or concision suggestions
belong in `language_issues` and are editorial issues. Only report a `missing_fact` when
that fact is explicitly present in the story brief or required outline facts. Never
demand explanations or details that the source does not provide. Return JSON only
matching the supplied schema.

Schema:
{output_schema}
