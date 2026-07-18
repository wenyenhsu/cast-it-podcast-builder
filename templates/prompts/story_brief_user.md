# Grounded Story Brief (v2.0.0)

Create a source-grounded story brief in {language}. Use only the supplied article.

Article ID: {article_id}
Title: {article_title}
Existing summary: {article_summary}

<<<ARTICLE_START>>>
{article_content}
<<<ARTICLE_END>>>

Rules:
- Every must-cover claim needs a short evidence excerpt or faithful paraphrase.
- Do not invent people, numbers, dates, events, quotations, or causal relationships.
- Put ambiguous or incomplete information in `uncertainties`.
- Put tempting but unsupported discussion topics in `unsupported_topics`.
- Keep the original article ID exactly unchanged.
- Return JSON only matching the supplied schema.

Schema:
{output_schema}
