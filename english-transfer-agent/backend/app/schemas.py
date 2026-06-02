from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


CardType = Literal["Pattern", "Grammar", "Chunk"]


class CardSource(BaseModel):
    title: str
    site: str
    url: str


class LearningCard(BaseModel):
    id: str
    type: CardType
    title: str
    source: CardSource
    originalReference: str
    extractedFromOriginal: str
    target: str
    referenceExample: str
    chinesePrompt: str
    expectedAnswer: str
    mustContain: str


class LearningCardSet(BaseModel):
    cards: list[LearningCard]


class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    snippet: str
    site: str


class Mistake(BaseModel):
    type: Literal["pattern", "grammar", "naturalness", "word_choice", "structure"]
    original: str
    correction: str
    explanationChinese: str
    reviewItem: str


class MemoryItemToSave(BaseModel):
    type: Literal["PATTERN", "GRAMMAR", "CHUNK", "NATURALNESS"]
    text: str
    priority: Literal["low", "medium", "high"]


class MemoryDecision(BaseModel):
    action: Literal["mark_known", "save_for_review", "save_as_weak", "none"]
    reasonChinese: str
    itemsToSave: list[MemoryItemToSave] = Field(default_factory=list)


class AnswerEvaluation(BaseModel):
    score: int
    status: str
    targetUsed: bool
    targetUsageQuality: Literal["failed", "partial", "good", "excellent"]
    adviceChinese: str
    teacherResponseChinese: str
    mainTeachingPoint: str | None = None
    microLessonChinese: str | None = None
    retryPromptChinese: str | None = None
    followUpPromptChinese: str | None = None
    sentenceFrame: str | None = None
    correctedAnswer: str
    naturalVersion: str
    advancedVersion: str
    mistakes: list[Mistake]
    memoryDecision: MemoryDecision
    nextAction: Literal["try_again", "give_hint", "micro_lesson", "follow_up_question", "next_card", "finish_round"]


class PracticedItem(BaseModel):
    cardTitle: str
    target: str
    score: int
    memoryAction: str


class MistakeToRemember(BaseModel):
    mistake: str
    correction: str
    ruleChinese: str
    example: str


class ReviewPlanItem(BaseModel):
    item: str
    type: Literal["Pattern", "Grammar", "Chunk", "Naturalness"]
    reviewAfterDays: int


class RoundSummary(BaseModel):
    practicedItems: list[PracticedItem]
    whatUserDidWell: list[str]
    mistakesToRemember: list[MistakeToRemember]
    weakItems: list[str]
    knownItemsAdded: list[str]
    reviewPlan: list[ReviewPlanItem]


class StartRequest(BaseModel):
    topic: Literal["random", "technology", "culture", "science", "psychology", "lifestyle"] = "random"
    level: str = "B2-C1"
    userId: str = "default-user"


class StartResponse(BaseModel):
    sessionId: str
    cards: list[LearningCard]


class AnswerRequest(BaseModel):
    sessionId: str
    cardId: str
    userAnswer: str
    attemptNumber: int | None = None


class FinishRequest(BaseModel):
    sessionId: str
