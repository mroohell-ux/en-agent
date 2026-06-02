from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import (
    AnswerEvaluation,
    CardSource,
    LearningCard,
    LearningCardSet,
    MemoryDecision,
    MemoryItemToSave,
    Mistake,
    MistakeToRemember,
    PracticedItem,
    ReviewPlanItem,
    RoundSummary,
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
        lower_prompt = prompt.lower()
        user_answer = prompt.split("UserAnswer:", 1)[1].strip() if "UserAnswer:" in prompt else prompt
        lower_answer = user_answer.lower()
        target_phrase = "plays a key role in"
        if "a lack of" in lower_prompt:
            target_phrase = "a lack of"
        elif "buffer against" in lower_prompt:
            target_phrase = "buffer against"

        target_used = target_phrase in lower_answer
        grammar_issue = any(bad in lower_answer for bad in [" in improve", " in reduce", " in turn", " in learn"])
        excellent = target_used and not grammar_issue and any(word in lower_answer for word in ["consistent", "clear", "good testing", "plays a key role in turning"])

        if not target_used:
            return AnswerEvaluation(
                score=45,
                status="needs_target_transfer",
                targetUsed=False,
                targetUsageQuality="failed",
                adviceChinese="这次的重点不是普通翻译，而是把目标表达迁移到新语境里。",
                teacherResponseChinese="你表达了大概意思，但还没有使用这张卡要训练的目标表达。先套用句型，再考虑细节。",
                mainTeachingPoint=f"Use the target expression: {target_phrase}",
                microLessonChinese=None,
                retryPromptChinese="请重新回答原来的中文提示，并尽量使用目标表达。",
                followUpPromptChinese=None,
                sentenceFrame="X plays a key role in doing Y." if target_phrase == "plays a key role in" else f"Use: {target_phrase} + your idea.",
                correctedAnswer="Consistent output practice plays a key role in turning passive English into active English.",
                naturalVersion="Consistent speaking and writing practice plays a key role in turning passive English into active use.",
                advancedVersion="Sustained output practice plays a key role in converting passive competence into active command.",
                mistakes=[Mistake(type="pattern", original="missing target expression", correction=f"use {target_phrase}", explanationChinese="需要迁移目标表达，而不只是表达意思。", reviewItem=target_phrase)],
                memoryDecision=MemoryDecision(
                    action="save_as_weak",
                    reasonChinese="未成功迁移目标表达，需要作为弱项继续练。",
                    itemsToSave=[MemoryItemToSave(type="PATTERN", text=target_phrase, priority="high")],
                ),
                nextAction="give_hint",
            )

        if grammar_issue:
            return AnswerEvaluation(
                score=72,
                status="target_used_with_grammar_issue",
                targetUsed=True,
                targetUsageQuality="partial",
                adviceChinese="你已经用了目标表达，下一步要修正结构里的语法问题。",
                teacherResponseChinese="你成功用了目标表达，但 in improve 要改成 in improving。",
                mainTeachingPoint="介词后接动名词 -ing",
                microLessonChinese="介词后面通常接动名词，比如 in improving, in learning, in reducing。",
                retryPromptChinese="请用英文表达：每天阅读在扩大词汇量方面起着关键作用。",
                followUpPromptChinese=None,
                sentenceFrame="X plays a key role in doing Y.",
                correctedAnswer="Output practice plays a key role in improving spoken English.",
                naturalVersion="Output practice plays a key role in improving spoken English.",
                advancedVersion="Consistent output practice plays a key role in developing fluent spoken English.",
                mistakes=[Mistake(type="grammar", original="in improve", correction="in improving", explanationChinese="介词 in 后面要接动名词 improving。", reviewItem="preposition + verb-ing")],
                memoryDecision=MemoryDecision(
                    action="save_for_review",
                    reasonChinese="目标表达已迁移，但语法点需要复习。",
                    itemsToSave=[MemoryItemToSave(type="GRAMMAR", text="preposition + verb-ing", priority="medium")],
                ),
                nextAction="micro_lesson",
            )

        return AnswerEvaluation(
            score=95 if excellent else 84,
            status="excellent" if excellent else "good_follow_up",
            targetUsed=True,
            targetUsageQuality="excellent" if excellent else "good",
            adviceChinese="目标表达迁移成功。继续用同一个表达换一个语境，会让它变成主动能力。",
            teacherResponseChinese="非常自然，目标表达和句子结构都用得很好。" if excellent else "很好，你已经把目标表达迁移到了新语境里。现在再换一个场景巩固一下。",
            mainTeachingPoint="目标表达迁移成功",
            microLessonChinese=None,
            retryPromptChinese=None,
            followUpPromptChinese=None if excellent else "请用英文表达：清晰的反馈在提高团队协作方面起着关键作用。",
            sentenceFrame="X plays a key role in doing Y." if target_phrase == "plays a key role in" else None,
            correctedAnswer=user_answer,
            naturalVersion=user_answer,
            advancedVersion="Sustained output practice plays a key role in converting passive competence into active command.",
            mistakes=[],
            memoryDecision=MemoryDecision(
                action="mark_known" if excellent else "save_for_review",
                reasonChinese="第一次高质量完成，可作为候选已掌握。" if excellent else "表现不错，但还需要一次换语境巩固。",
                itemsToSave=[MemoryItemToSave(type="PATTERN", text=target_phrase, priority="low")],
            ),
            nextAction="next_card" if excellent else "follow_up_question",
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
