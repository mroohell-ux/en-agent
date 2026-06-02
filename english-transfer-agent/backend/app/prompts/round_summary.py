from __future__ import annotations

import json


def build_round_summary_prompt(round_data: dict) -> str:
    return (
        "Summarize this study round. Return JSON only.\n"
        f"RoundData(JSON): {json.dumps(round_data, ensure_ascii=False)}\n\n"
        "Must identify:\n"
        "- practiced items\n"
        "- what user did well\n"
        "- mistakes to remember\n"
        "- weak items\n"
        "- known items added\n"
        "- review plan\n"
    )
