from __future__ import annotations

import json
import os
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

import httpx
from pydantic import BaseModel

from app.schemas import (
    AnswerEvaluation,
    ArticleLesson,
    ArticleSource,
    CardSource,
    LearningCard,
    LearningCardSet,
    LessonSummary,
    LessonProgress,
    Mistake,
    MistakeToRemember,
    PracticedItem,
    RetellTask,
    RoundSummary,
    TeacherCorrection,
    TeacherQuestion,
    UsefulLanguageItem,
    IeltsTasks,
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

    @abstractmethod
    def generate_article_lesson(self, prompt: str) -> ArticleLesson:
        raise NotImplementedError

    @abstractmethod
    def evaluate_speaking_answer(self, prompt: str) -> TeacherCorrection:
        raise NotImplementedError

    @abstractmethod
    def summarize_article_lesson(self, prompt: str) -> LessonSummary:
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
            nextAction="next_card" if excellent else "follow_up_question",
        )

    def summarize_round(self, prompt: str) -> RoundSummary:
        return RoundSummary(
            practicedItems=[PracticedItem(cardTitle="Key role pattern", target="X plays a key role in Y.", score=85)],
            whatUserDidWell=["能够理解原句含义并尝试迁移结构"],
            mistakesToRemember=[MistakeToRemember(mistake="in improve", correction="in improving", ruleChinese="介词后动词用 -ing", example="plays a key role in improving")],
            weakItems=["preposition + verb-ing"],
            suggestedNextPractice=["用本轮练过的表达各造一个新句子；这只是练习建议，不会写入长期复习计划。"],
        )


    def generate_article_lesson(self, prompt: str) -> ArticleLesson:
        include_ielts = "IncludeIelts: true" in prompt
        raw_text = prompt.split("ArticleText:", 1)[1].strip() if "ArticleText:" in prompt else ""
        raw_lower = raw_text.lower()
        is_vance = "cat ladies" in raw_lower or "jd vance" in raw_lower or "childless" in raw_lower
        title = "JD Vance's 'childless cat ladies' comment sparks backlash" if is_vance else "Article-based speaking lesson"
        source = ArticleSource(
            title=title,
            url=_extract_prompt_value(prompt, "ArticleUrl") or None,
            site="Pasted article" if not _extract_prompt_value(prompt, "ArticleUrl") else "Article URL",
            rawText=raw_text or "A public comment did not land well and sparked a wider debate about stereotypes, family choices, and political language.",
            publishedAt=None,
        )
        questions = [
            TeacherQuestion(id="q-comprehension", type="comprehension", question="What phrase or comment caused public anger?", expectedIdeas=["Identify the controversial phrase", "Explain who reacted to it"], usefulExpressionHint="unleash fury"),
            TeacherQuestion(id="q-explanation", type="explanation", question="Why did many people see the phrase as sexist or unfair?", expectedIdeas=["It reduced women to family status", "It suggested childless people have less stake in society"], usefulExpressionHint="take issue with"),
            TeacherQuestion(id="q-opinion", type="opinion", question="Do you think politicians should comment on people’s family choices? Why or why not?", expectedIdeas=["Give a clear opinion", "Support it with one reason"], usefulExpressionHint="did not land well"),
            TeacherQuestion(id="q-personal", type="personal_connection", question="Are there similar stereotypes about marriage, children, or gender roles in your culture?", expectedIdeas=["Connect the article to your own context", "Give a concrete example"], usefulExpressionHint="a direct stake in"),
            TeacherQuestion(id="q-advanced", type="advanced_discussion", question="Why do old stereotypes survive even when society changes?", expectedIdeas=["Discuss habit, media, politics, or social pressure", "Use an abstract explanation"], usefulExpressionHint="harmful historical roots"),
        ]
        useful_language = [
            UsefulLanguageItem(id="ul-unleash-fury", category="expression", text="unleash fury", meaning="cause a strong angry public reaction", fromArticle="the comment unleashed fury", whyUseful="It helps you describe backlash in news or social discussions.", example="The decision unleashed fury among users.", reusePrompt="Use 'unleash fury' to describe a comment, policy, joke, or product update."),
            UsefulLanguageItem(id="ul-did-not-land-well", category="expression", text="did not land well", meaning="was received badly", fromArticle="his comments did not land well", whyUseful="It sounds natural when judging how people reacted to a message.", example="The joke did not land well in the meeting.", reusePrompt="Use 'did not land well' to describe a joke, comment, decision, or product update."),
            UsefulLanguageItem(id="ul-take-issue-with", category="expression", text="take issue with", meaning="disagree strongly with something", fromArticle="critics took issue with the phrase", whyUseful="It is a precise speaking phrase for disagreement.", example="Many parents took issue with the school’s decision.", reusePrompt="Use 'take issue with' to explain what people objected to."),
            UsefulLanguageItem(id="ul-direct-stake", category="expression", text="have a direct stake in", meaning="be personally affected by or invested in something", fromArticle="people with children have a more direct stake", whyUseful="It helps you discuss responsibility, politics, and incentives.", example="Young people have a direct stake in climate policy.", reusePrompt="Use 'have a direct stake in' to talk about a social issue."),
            UsefulLanguageItem(id="ul-backlash", category="vocabulary", text="backlash", meaning="a strong negative reaction", fromArticle="the backlash grew online", whyUseful="It is common in news, politics, and workplace discussions.", example="The company faced backlash after changing its privacy policy.", reusePrompt="Use 'backlash' to describe a public reaction."),
            UsefulLanguageItem(id="ul-saw-it-as", category="sentence_pattern", text="see it as + adjective/noun", meaning="interpret something in a particular way", fromArticle="many saw it as sexist", whyUseful="It helps you report other people’s reactions without overclaiming.", example="Some users saw it as a step backward.", reusePrompt="Use 'saw it as' to explain how a group interpreted something."),
        ]
        ielts = None
        if include_ielts:
            ielts = IeltsTasks(
                listening={"transcript": "A short news report summarizes the controversy and the public response.", "questions": ["What comment caused backlash?", "Who criticized it?"]},
                reading={"questions": ["What is the main idea?", "True/False/Not Given: Everyone agreed with the comment."], "vocabularyInContext": ["backlash", "stake"]},
                writing={"task2": "Public figures should avoid commenting on private family choices. To what extent do you agree?"},
                speaking={"part1": ["Do people in your culture talk a lot about family choices?"], "part2": "Describe a public comment that caused debate.", "part3": ["Why can stereotypes be politically powerful?"]},
            )
        return ArticleLesson(
            id="lesson-mock",
            userId=_extract_prompt_value(prompt, "UserId") or "default-user",
            source=source,
            level=_extract_prompt_value(prompt, "Level") or "B2-C1",
            mainIdea="The article explains how a political comment about childless women triggered backlash because many people saw it as sexist and dismissive of people without children.",
            keyPoints=["A phrase about 'childless cat ladies' caused anger.", "Critics argued that it relied on old gender stereotypes.", "The debate became about family choices, political power, and who has a stake in society."],
            retellTask=RetellTask(prompt="What is the main idea of this article? Say it in your own words in 40–60 seconds.", targetSpeakingSeconds=50, hints=["Start with: The article is mainly about...", "Mention the comment, the backlash, and why people objected."], expectedContentPoints=["Identify the controversial comment", "Explain the backlash", "Mention stereotypes or family choices"]),
            questions=questions,
            usefulLanguage=useful_language,
            ieltsTasks=ielts,
            progress=LessonProgress(),
        )

    def evaluate_speaking_answer(self, prompt: str) -> TeacherCorrection:
        transcript = prompt.split("Transcript:", 1)[1].strip() if "Transcript:" in prompt else prompt
        lower = transcript.lower()
        mistakes = []
        if "people angry about" in lower:
            mistakes.append(Mistake(type="expression", original="people angry about", correction="backlash against", explanation="'Backlash against' is more natural for public criticism.", explanationChinese="讨论公众批评时，backlash against 更自然。", reviewItem="people angry about → backlash against"))
        if "bad history" in lower:
            mistakes.append(Mistake(type="expression", original="bad history", correction="a darker history / harmful historical roots", explanation="This sounds more natural when discussing social or historical context.", explanationChinese="讨论社会或历史语境时，这样更自然。", reviewItem="bad history → harmful historical roots"))
        if "it is sexist" in lower:
            mistakes.append(Mistake(type="naturalness", original="it is sexist", correction="they saw it as sexist", explanation="Use reporting language when describing other people's reaction.", explanationChinese="描述他人反应时，用 saw it as 更准确。", reviewItem="it is sexist → they saw it as sexist"))
        if not mistakes:
            mistakes.append(Mistake(type="structure", original="unclear focus", correction="Start with the main point, then give one reason.", explanation="Speaking answers sound stronger when the logic is easy to follow.", explanationChinese="口语答案先说主旨，再给理由，会更清楚。", reviewItem="main point → one reason"))
        natural = "The article is mainly about the backlash against JD Vance’s 'childless cat ladies' comment. Many people took issue with it because they saw it as sexist and dismissive of people who do not have children."
        return TeacherCorrection(
            score=82 if len(mistakes) <= 1 else 74,
            overallFeedback="Good start. Your answer connects to the article, but make it more natural and more clearly structured for speaking.",
            correctedAnswer=natural,
            naturalVersion=natural,
            advancedVersion="The article shows how one political phrase can unleash fury when it taps into older stereotypes about gender, family choices, and who is seen as having a direct stake in society.",
            mistakes=mistakes[:3],
            keyImprovements=["Use 'backlash against...' instead of 'people angry about...'.", "Use 'they saw it as sexist' instead of directly saying 'it is sexist'.", "State the main idea first, then add one clear reason."],
            repeatPrompt=f"Now repeat this improved version aloud: {natural}",
            nextAction="repeat_better_version",
        )

    def summarize_article_lesson(self, prompt: str) -> LessonSummary:
        return LessonSummary(
            lessonId=_extract_prompt_value(prompt, "LessonId") or "lesson-mock",
            whatUserDidWell=["You answered from the article instead of giving a generic opinion.", "You practiced turning passive understanding into spoken output."],
            repeatedMistakes=[Mistake(type="expression", original="people angry about", correction="backlash against", explanation="Use this for public criticism.", explanationChinese="公众批评更常用 backlash against。", reviewItem="backlash against")],
            usefulExpressionsLearned=[UsefulLanguageItem(id="ul-did-not-land-well", category="expression", text="did not land well", meaning="was received badly", fromArticle="his comments did not land well", whyUseful="Useful for reactions.", example="The joke did not land well.", reusePrompt="Use it to describe a public reaction.")],
            suggestedNextPractice=["Repeat your natural version once more.", "Answer one advanced discussion question using 'have a direct stake in'.", "Review: backlash against; did not land well; take issue with."],
        )


SchemaModel = TypeVar("SchemaModel", bound=BaseModel)


class OpenAiCompatibleProvider(AiProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float,
        temperature: float,
        max_tokens: int,
        missing_key_error: str,
        response_format_builder,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.missing_key_error = missing_key_error
        self.response_format_builder: Callable[[type[SchemaModel], str], dict[str, Any]] = response_format_builder

    def generate_cards(self, prompt: str) -> LearningCardSet:
        return self._chat_structured(prompt, LearningCardSet, "LearningCardSet")

    def evaluate_answer(self, prompt: str) -> AnswerEvaluation:
        return self._chat_structured(prompt, AnswerEvaluation, "AnswerEvaluation")

    def summarize_round(self, prompt: str) -> RoundSummary:
        return self._chat_structured(prompt, RoundSummary, "RoundSummary")

    def generate_article_lesson(self, prompt: str) -> ArticleLesson:
        return self._chat_structured(prompt, ArticleLesson, "ArticleLesson")

    def evaluate_speaking_answer(self, prompt: str) -> TeacherCorrection:
        return self._chat_structured(prompt, TeacherCorrection, "TeacherCorrection")

    def summarize_article_lesson(self, prompt: str) -> LessonSummary:
        return self._chat_structured(prompt, LessonSummary, "LessonSummary")

    def _chat_structured(self, prompt: str, schema_model: type[SchemaModel], schema_name: str) -> SchemaModel:
        if not self.api_key:
            raise RuntimeError(self.missing_key_error)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the AI backend for an English transfer-learning app. "
                        "Return only JSON that matches the requested schema. "
                        "Do not include markdown, commentary, or long-term memory actions."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        response_format = self.response_format_builder(schema_model, schema_name)
        if response_format is not None:
            payload["response_format"] = response_format

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = self._parse_json_content(content)
        parsed = _normalize_schema_payload(schema_model, parsed)
        return schema_model.model_validate(parsed)

    @staticmethod
    def _parse_json_content(content):
        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise ValueError("Model response content was not a JSON string or object")

        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        return json.loads(stripped)


class GrokProvider(OpenAiCompatibleProvider):
    def __init__(self) -> None:
        super().__init__(
            api_key=os.getenv("XAI_API_KEY", ""),
            model=os.getenv("XAI_MODEL", "grok-4.3"),
            base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
            timeout=float(os.getenv("XAI_TIMEOUT_SECONDS", "60")),
            temperature=float(os.getenv("XAI_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("XAI_MAX_TOKENS", "4096")),
            missing_key_error="XAI_API_KEY is required when AI_PROVIDER=grok",
            response_format_builder=_build_json_schema_response_format,
        )


class AlibabaProvider(OpenAiCompatibleProvider):
    def __init__(self) -> None:
        super().__init__(
            api_key=os.getenv("ALIBABA_API_KEY", os.getenv("DASHSCOPE_API_KEY", "")),
            model=os.getenv("ALIBABA_MODEL", os.getenv("DASHSCOPE_MODEL", "qwen-plus")),
            base_url=os.getenv("ALIBABA_BASE_URL", os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")),
            timeout=float(os.getenv("ALIBABA_TIMEOUT_SECONDS", os.getenv("DASHSCOPE_TIMEOUT_SECONDS", "60"))),
            temperature=float(os.getenv("ALIBABA_TEMPERATURE", os.getenv("DASHSCOPE_TEMPERATURE", "0.2"))),
            max_tokens=int(os.getenv("ALIBABA_MAX_TOKENS", os.getenv("DASHSCOPE_MAX_TOKENS", "4096"))),
            missing_key_error="ALIBABA_API_KEY or DASHSCOPE_API_KEY is required when AI_PROVIDER=alibaba",
            response_format_builder=_build_json_object_response_format,
        )


def _build_json_schema_response_format(schema_model: type[SchemaModel], schema_name: str) -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "schema": schema_model.model_json_schema(),
        },
    }


def _build_json_object_response_format(schema_model: type[SchemaModel], schema_name: str) -> dict:
    return {"type": "json_object"}


def _normalize_schema_payload(schema_model: type[SchemaModel], payload: Any) -> Any:
    if schema_model is LearningCardSet and isinstance(payload, dict):
        cards = payload.get("cards")
        if isinstance(cards, list):
            payload = dict(payload)
            payload["cards"] = [_normalize_learning_card(card, index) for index, card in enumerate(cards, start=1)]
    elif schema_model is AnswerEvaluation and isinstance(payload, dict):
        payload = _normalize_answer_evaluation(payload)
    elif schema_model is RoundSummary and isinstance(payload, dict):
        payload = _normalize_round_summary(payload)
    return payload


def _normalize_learning_card(card: Any, index: int) -> Any:
    if not isinstance(card, dict):
        return card

    normalized = dict(card)
    normalized["id"] = str(
        normalized.get("id")
        or normalized.get("cardId")
        or normalized.get("card_id")
        or f"card-{index}-{uuid.uuid4().hex[:8]}"
    )

    normalized_type = (
        normalized.get("type")
        or normalized.get("cardType")
        or normalized.get("category")
        or normalized.get("kind")
        or "Pattern"
    )
    normalized["type"] = _normalize_card_type(str(normalized_type))

    source = normalized.get("source")
    if not isinstance(source, dict):
        source = {}
    source = dict(source)
    source["title"] = str(
        source.get("title")
        or normalized.get("sourceTitle")
        or normalized.get("articleTitle")
        or normalized.get("title")
        or normalized.get("target")
        or normalized.get("targetExpression")
        or f"Card {index}"
    )
    source["site"] = str(
        source.get("site")
        or normalized.get("sourceSite")
        or normalized.get("site")
        or normalized.get("publisher")
        or ""
    )
    source["url"] = str(
        source.get("url")
        or normalized.get("sourceUrl")
        or normalized.get("url")
        or normalized.get("articleUrl")
        or ""
    )
    normalized["source"] = source

    normalized["title"] = str(
        normalized.get("title")
        or normalized.get("cardTitle")
        or normalized.get("label")
        or normalized.get("target")
        or normalized.get("targetExpression")
        or source["title"]
    )
    normalized["originalReference"] = str(
        normalized.get("originalReference")
        or normalized.get("referenceSentence")
        or normalized.get("reference")
        or normalized.get("sourceSentence")
        or normalized.get("originalSentence")
        or ""
    )
    normalized["extractedFromOriginal"] = str(
        normalized.get("extractedFromOriginal")
        or normalized.get("extractedTarget")
        or normalized.get("extractedChunk")
        or normalized.get("keyExpression")
        or normalized.get("target")
        or normalized.get("targetExpression")
        or ""
    )
    normalized["target"] = str(
        normalized.get("target")
        or normalized.get("targetExpression")
        or normalized.get("expression")
        or normalized.get("pattern")
        or normalized.get("focus")
        or normalized["extractedFromOriginal"]
    )
    normalized["referenceExample"] = str(
        normalized.get("referenceExample")
        or normalized.get("exampleSentence")
        or normalized.get("rewriteExample")
        or normalized.get("example")
        or normalized.get("sampleAnswer")
        or ""
    )
    normalized["chinesePrompt"] = str(
        normalized.get("chinesePrompt")
        or normalized.get("promptChinese")
        or normalized.get("transferPromptChinese")
        or normalized.get("questionChinese")
        or normalized.get("prompt")
        or ""
    )
    normalized["expectedAnswer"] = str(
        normalized.get("expectedAnswer")
        or normalized.get("expectedEnglish")
        or normalized.get("exampleAnswer")
        or normalized.get("idealAnswer")
        or normalized.get("sampleAnswer")
        or normalized["referenceExample"]
    )
    normalized["mustContain"] = str(
        normalized.get("mustContain")
        or normalized.get("mustUse")
        or normalized.get("requiredPhrase")
        or normalized.get("requiredExpression")
        or normalized["target"]
    )
    return normalized


def _normalize_card_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"pattern", "sentence pattern"}:
        return "Pattern"
    if normalized in {"grammar", "grammatical point"}:
        return "Grammar"
    if normalized in {"chunk", "phrase", "collocation"}:
        return "Chunk"
    return "Pattern"


def _normalize_answer_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["score"] = int(normalized.get("score", 0) or 0)
    normalized["targetUsed"] = _coerce_bool(normalized.get("targetUsed"))
    normalized["targetUsageQuality"] = _normalize_target_usage_quality(
        normalized.get("targetUsageQuality"),
        normalized["targetUsed"],
        normalized["score"],
    )
    normalized["adviceChinese"] = str(
        normalized.get("adviceChinese")
        or normalized.get("advice")
        or normalized.get("feedbackChinese")
        or normalized.get("teacherResponseChinese")
        or normalized.get("teacherResponse")
        or ""
    )
    normalized["teacherResponseChinese"] = str(
        normalized.get("teacherResponseChinese")
        or normalized.get("teacherResponse")
        or normalized.get("feedbackChinese")
        or normalized["adviceChinese"]
        or ""
    )
    normalized["status"] = str(normalized.get("status") or "evaluated")
    normalized["mainTeachingPoint"] = normalized.get("mainTeachingPoint") or normalized.get("teachingPoint")
    normalized["microLessonChinese"] = normalized.get("microLessonChinese") or normalized.get("microLesson")
    normalized["retryPromptChinese"] = normalized.get("retryPromptChinese") or normalized.get("retryPrompt")
    normalized["followUpPromptChinese"] = normalized.get("followUpPromptChinese") or normalized.get("followUpPrompt")
    normalized["sentenceFrame"] = normalized.get("sentenceFrame") or normalized.get("frame")
    normalized["correctedAnswer"] = str(
        normalized.get("correctedAnswer")
        or normalized.get("correction")
        or normalized.get("revisedAnswer")
        or normalized.get("betterAnswer")
        or ""
    )
    normalized["naturalVersion"] = str(
        normalized.get("naturalVersion")
        or normalized.get("naturalAnswer")
        or normalized.get("moreNaturalVersion")
        or normalized["correctedAnswer"]
    )
    normalized["advancedVersion"] = str(
        normalized.get("advancedVersion")
        or normalized.get("advancedAnswer")
        or normalized.get("strongerVersion")
        or normalized["naturalVersion"]
    )
    normalized["mistakes"] = _normalize_mistakes(normalized.get("mistakes"))
    normalized["nextAction"] = _normalize_next_action(
        normalized.get("nextAction"),
        normalized["targetUsed"],
        normalized["targetUsageQuality"],
        normalized["mistakes"],
    )
    return normalized


def _normalize_round_summary(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["whatUserDidWell"] = normalized.get("whatUserDidWell") or normalized.get("strengths") or []
    normalized["suggestedNextPractice"] = normalized.get("suggestedNextPractice") or normalized.get("nextPractice") or []
    return normalized


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1", "used", "present"}
    return False


def _normalize_target_usage_quality(value: Any, target_used: bool, score: int) -> str:
    normalized = str(value or "").strip().lower()
    mapping = {
        "none": "failed",
        "missing": "failed",
        "not_used": "failed",
        "failed": "failed",
        "weak": "partial",
        "partial": "partial",
        "ok": "good",
        "good": "good",
        "strong": "excellent",
        "excellent": "excellent",
    }
    if normalized in mapping:
        return mapping[normalized]
    if not target_used:
        return "failed"
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    return "partial"


def _normalize_mistakes(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized_mistakes: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            normalized_mistakes.append({
                "type": _normalize_mistake_type(item.get("type")),
                "original": str(item.get("original") or item.get("mistake") or item.get("issue") or ""),
                "correction": str(item.get("correction") or item.get("fix") or item.get("suggestion") or ""),
                "explanationChinese": str(item.get("explanationChinese") or item.get("explanation") or "需要修正这个问题。"),
                "reviewItem": str(item.get("reviewItem") or item.get("focus") or item.get("correction") or item.get("original") or ""),
            })
            continue

        if isinstance(item, str):
            normalized_mistakes.append({
                "type": _infer_mistake_type(item),
                "original": item,
                "correction": "",
                "explanationChinese": "需要根据老师反馈修正这个问题。",
                "reviewItem": item,
            })
    return normalized_mistakes


def _normalize_mistake_type(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"pattern", "grammar", "naturalness", "word_choice", "structure", "vocabulary", "expression", "logic"}:
        return normalized
    return _infer_mistake_type(normalized)


def _infer_mistake_type(text: str) -> str:
    lowered = text.lower()
    if "grammar" in lowered or "preposition" in lowered or "tense" in lowered or "plural" in lowered:
        return "grammar"
    if "word" in lowered or "vocabulary" in lowered or "choice" in lowered:
        return "vocabulary"
    if "natural" in lowered or "awkward" in lowered:
        return "naturalness"
    if "structure" in lowered or "sentence" in lowered or "subject" in lowered:
        return "structure"
    return "pattern"


def _normalize_next_action(value: Any, target_used: bool, target_usage_quality: str, mistakes: list[dict[str, str]]) -> str:
    normalized = str(value or "").strip().lower()
    mapping = {
        "try_again": "try_again",
        "retry": "try_again",
        "give_hint": "give_hint",
        "hint": "give_hint",
        "micro_lesson": "micro_lesson",
        "lesson": "micro_lesson",
        "follow_up_question": "follow_up_question",
        "followup": "follow_up_question",
        "next_card": "next_card",
        "next": "next_card",
        "finish_round": "finish_round",
        "finish": "finish_round",
    }
    if normalized in mapping:
        return mapping[normalized]
    if not target_used:
        return "give_hint"
    if mistakes and target_usage_quality in {"failed", "partial"}:
        return "micro_lesson"
    if target_usage_quality == "good":
        return "follow_up_question"
    return "next_card"


def build_ai_provider(name: str) -> AiProvider:
    normalized = (name or "mock").lower().strip()
    if normalized == "grok":
        return GrokProvider()
    if normalized in {"alibaba", "dashscope", "qwen"}:
        return AlibabaProvider()
    return MockAiProvider()


def _extract_prompt_value(prompt: str, key: str) -> str:
    prefix = f"{key}:"
    for line in prompt.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""
