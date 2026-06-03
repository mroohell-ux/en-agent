from __future__ import annotations

from typing import Literal, Optional
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


class AnswerEvaluation(BaseModel):
    score: int
    status: str
    targetUsed: bool
    targetUsageQuality: Literal["failed", "partial", "good", "excellent"]
    adviceChinese: str
    teacherResponseChinese: str
    mainTeachingPoint: Optional[str] = None
    microLessonChinese: Optional[str] = None
    retryPromptChinese: Optional[str] = None
    followUpPromptChinese: Optional[str] = None
    sentenceFrame: Optional[str] = None
    correctedAnswer: str
    naturalVersion: str
    advancedVersion: str
    mistakes: list[Mistake]
    nextAction: Literal["try_again", "give_hint", "micro_lesson", "follow_up_question", "next_card", "finish_round"]


class PracticedItem(BaseModel):
    cardTitle: str
    target: str
    score: int


class MistakeToRemember(BaseModel):
    mistake: str
    correction: str
    ruleChinese: str
    example: str


class RoundSummary(BaseModel):
    practicedItems: list[PracticedItem]
    whatUserDidWell: list[str]
    mistakesToRemember: list[MistakeToRemember]
    weakItems: list[str]
    suggestedNextPractice: list[str] = Field(default_factory=list)


class StartRequest(BaseModel):
    topic: Literal["random", "technology", "culture", "science", "psychology", "lifestyle"] = "random"
    level: str = "B2-C1"
    userId: str = "default-user"


class StartResponse(BaseModel):
    sessionId: str
    cards: list[LearningCard]
    sourceArticles: list[SearchResult] = Field(default_factory=list)


class AnswerRequest(BaseModel):
    sessionId: str
    cardId: str
    userAnswer: str
    attemptNumber: Optional[int] = None


class FinishRequest(BaseModel):
    sessionId: str
