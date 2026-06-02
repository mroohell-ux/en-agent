from __future__ import annotations

import json


def build_round_summary_prompt(round_data: dict) -> str:
    return (
        "Summarize this study round only. Return JSON only.\n"
        f"RoundData(JSON): {json.dumps(round_data, ensure_ascii=False)}\n\n"
        "Do not update or schedule long-term learning memory.\n"
        "Give review suggestions as plain text advice only.\n"
        "Must identify:\n"
        "- practiced items\n"
        "- what the user did well\n"
        "- mistakes to remember\n"
        "- weak items observed in this round\n"
        "- suggested next practice\n"
    )
