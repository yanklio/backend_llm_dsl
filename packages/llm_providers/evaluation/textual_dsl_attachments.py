"""Textual DSL reference and few-shot attachments for LLM prompts."""

TEXTUAL_DSL_SPEC = """TEXTUAL DSL REFERENCE

Allowed primitive field types:
- string
- number
- boolean
- date

Do not use TypeScript syntax in the textual DSL.
Use the @ annotation syntax for validation and constraints.
"""

TEXTUAL_DSL_EXAMPLES = """TEXTUAL DSL EXAMPLES

Example: Blog with authors and posts

app BlogApp {
  database: sqlite @path("./data/app.db")
  features: [cors, swagger]
}

entity Author {
  name: string @required @minLength(2) @maxLength(100)
  email: string @required @unique @email
  posts: Post[] @OneToMany(inverse: author)
}

entity Post {
  title: string @required @minLength(1)
  content: string @required
  author: Author @ManyToOne(inverse: posts)
}

module Authors for Author {
  route GET /authors -> Author[]
  route POST /authors -> Author
  route PATCH /authors/:id -> Author
  route DELETE /authors/:id -> void
}

module Posts for Post {
  route GET /posts -> Post[]
  route POST /posts -> Post
  route PATCH /posts/:id -> Post
  route DELETE /posts/:id -> void
}
"""


def textual_dsl_attachment(level: str) -> str:
    """Get textual DSL prompt attachment by level.

    Args:
        level: Attachment level ("spec", "fewshot", or "").

    Returns:
        str: The attachment content for the given level.
    """
    if level == "spec":
        return TEXTUAL_DSL_SPEC
    elif level == "fewshot":
        return TEXTUAL_DSL_SPEC + "\n" + TEXTUAL_DSL_EXAMPLES
    return ""
