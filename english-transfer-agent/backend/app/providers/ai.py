from __future__ import annotations

import os
from abc import ABC, abstractmethod

from app.schemas import (
    AnswerEvaluation,
    LearningCard,
    LearningCardSet,
    MemoryDecision,
    MemoryItemToSave,
    Mistake,
    RoundSummary,
    PracticedItem,
    MistakeToRemember,
    ReviewPlanItem,
    CardSource,
)


class AiProvider(ABC):
    @abstractmethod
    def generate_cards(self, prompt: str) -> LearningCardSet:
        raise NotImplementedError

    @abstractmethod
    def evaluate_answer(self, prompt: str) -> AnswerEvaluation:
        raise NotImplementedError

    @abstractmethod
    def summarize_round(self, prompt: str) -> RoundSummary:
        raise NotImplementedError


class MockAiProvider(AiProvider):
    def generate_cards(self, prompt: str) -> LearningCardSet:
        return LearningCardSet(cards=[
            LearningCard(
                id="card-1", type="Pattern", title="Key role pattern",
                source=CardSource(title="Ocean life and climate", site="Example Science", url="https://example.com/ocean-life"),
                originalReference="Two back-to-back expeditions in the Southwest Atlantic Ocean have highlighted the key role played by deep-sea organisms in locking away carbon and buffering against climate change.",
                extractedFromOriginal="highlighted the key role played by deep-sea organisms in locking away carbon",
                target="X plays a key role in Y.",
                referenceExample="Deep-sea organisms play a key role in locking away carbon.",
                chinesePrompt="请用英文表达：持续输出练习在把被动英语变成主动英语方面起着关键作用。",
                expectedAnswer="Consistent output practice plays a key role in turning passive English into active English.",
                mustContain="plays a key role in"
            ),
            LearningCard(
                id="card-2", type="Chunk", title="Lack of",
                source=CardSource(title="Team collaboration", site="Example Work", url="https://example.com/collaboration"),
                originalReference="The failure mainly came from a lack of clear communication between teams.",
                extractedFromOriginal="a lack of clear communication",
                target="a lack of + noun",
                referenceExample="The delay came from a lack of planning.",
                chinesePrompt="请用英文表达：这个项目的问题源于缺乏清晰的需求。",
                expectedAnswer="The project’s problems come from a lack of clear requirements.",
                mustContain="a lack of"
            ),
            LearningCard(
                id="card-3", type="Chunk", title="Buffer against",
                source=CardSource(title="Engineering quality", site="Example Engineering", url="https://example.com/testing"),
                originalReference="Strong testing practices can buffer against unexpected failures in production.",
                extractedFromOriginal="buffer against unexpected failures",
                target="buffer against something",
                referenceExample="Insurance can buffer against sudden financial loss.",
                chinesePrompt="请用英文表达：良好的测试可以减少生产环境 bug 带来的风险。",
                expectedAnswer="Good testing can buffer against risks caused by production bugs.",
                mustContain="buffer against"
            )
        ])

    def evaluate_answer(self, prompt: str) -> AnswerEvaluation:
        used = "plays a key role in" in prompt.lower() or "a lack of" in prompt.lower() or "buffer against" in prompt.lower()
        return AnswerEvaluation(
            score=88 if used else 62,
            status="good" if used else "needs_work",
            targetUsed=used,
            targetUsageQuality="good" if used else "failed",
            adviceChinese="重点不是逐词翻译，而是把目标表达迁移到新语境。",
            correctedAnswer="Consistent output practice plays a key role in turning passive English into active English.",
            naturalVersion="Consistent speaking and writing practice plays a key role in turning passive English into active use.",
            advancedVersion="Sustained output practice plays a key role in converting passive competence into active command.",
            mistakes=[] if used else [Mistake(type="pattern", original="no target pattern", correction="use target expression", explanationChinese="需要使用目标表达完成迁移训练", reviewItem="target transfer")],
            memoryDecision=MemoryDecision(
                action="mark_known" if used else "save_as_weak",
                reasonChinese="已正确迁移目标表达" if used else "表达了意思但未迁移目标结构",
                itemsToSave=[MemoryItemToSave(type="PATTERN", text="plays a key role in", priority="medium")]
            ),
            nextAction="next_card",
        )

    def summarize_round(self, prompt: str) -> RoundSummary:
        return RoundSummary(
            practicedItems=[PracticedItem(cardTitle="Key role pattern", target="X plays a key role in Y.", score=85, memoryAction="save_for_review")],
            whatUserDidWell=["能够理解原句含义并尝试迁移结构"],
            mistakesToRemember=[MistakeToRemember(mistake="in improve", correction="in improving", ruleChinese="介词后动词用 -ing", example="plays a key role in improving")],
            weakItems=["preposition + verb-ing"],
            knownItemsAdded=["a lack of + noun"],
            reviewPlan=[ReviewPlanItem(item="preposition + verb-ing", type="Grammar", reviewAfterDays=1)]
        )


class GrokProvider(MockAiProvider):
    pass


def build_ai_provider(name: str) -> AiProvider:
    if name == "grok":
        return GrokProvider()
    return MockAiProvider()
