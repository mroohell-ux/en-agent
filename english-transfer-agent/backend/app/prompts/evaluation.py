EVALUATION_PROMPT = """
Evaluate the user’s English answer.

Check:
- Did the user use the target expression?
- Did they use it correctly?
- Grammar mistakes
- Unnatural expressions
- Word choice
- Sentence structure
- Whether the item should go into known memory, weak memory, or review memory

Return JSON only.
""".strip()
