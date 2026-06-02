from __future__ import annotations

import json


def build_card_generation_prompt(topic: str, level: str, search_results: list[dict], memory: dict) -> str:
    return (
        "You are an English learning agent.\n\n"
        "The user can often understand English, but cannot actively use expressions.\n"
        "Your job: convert searched English references into active transfer cards.\n\n"
        f"Topic: {topic}\n"
        f"Level: {level}\n"
        f"SearchResults(JSON): {json.dumps(search_results, ensure_ascii=False)}\n"
        f"KnownMemoryToAvoid(JSON): {json.dumps({'knownTopics': memory.get('knownTopics', []), 'knownPatterns': memory.get('knownPatterns', []), 'knownChunks': memory.get('knownChunks', [])}, ensure_ascii=False)}\n"
        f"WeakMemoryToPreferIfNatural(JSON): {json.dumps({'weakGrammarPoints': memory.get('weakGrammarPoints', []), 'weakPatterns': memory.get('weakPatterns', [])}, ensure_ascii=False)}\n\n"
        "Rules:\n"
        "- Generate 1 to 10 learning cards based on learning value only.\n"
        "- Each card teaches exactly one Pattern, Grammar, or Chunk.\n"
        "- Each card must use one original reference sentence from search material.\n"
        "- Extract one reusable target from that reference.\n"
        "- Ask a DIFFERENT Chinese transfer prompt for each card.\n"
        "- chinesePrompt must be clear for ask-first UI.\n"
        "- No filler cards, no repeated known items.\n"
        "- Return JSON only with shape: {\"cards\":[...LearningCard...]}.\n"
    )
