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


MistakeType = Literal[
    "pattern",
    "grammar",
    "naturalness",
    "word_choice",
    "structure",
    "vocabulary",
    "expression",
    "logic",
]


class Mistake(BaseModel):
    type: MistakeType
    original: str
    correction: str
    explanation: str = ""
    explanationChinese: str = ""
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


class AnswerRequest(BaseModel):
    sessionId: str
    cardId: str
    userAnswer: str
    attemptNumber: Optional[int] = None


class FinishRequest(BaseModel):
    sessionId: str


QuestionType = Literal[
    "comprehension",
    "explanation",
    "opinion",
    "personal_connection",
    "advanced_discussion",
]
UsefulLanguageCategory = Literal["expression", "vocabulary", "grammar", "sentence_pattern"]
SpeakingTaskType = Literal["retell", "question", "useful_language", "ielts_speaking"]
LessonMode = Literal["speaking_first"]
CorrectionNextAction = Literal[
    "repeat_better_version",
    "answer_next_question",
    "reuse_expression_again",
    "review_mistakes",
    "finish_lesson",
]


class ArticleSource(BaseModel):
    title: str
    url: Optional[str] = None
    site: Optional[str] = None
    rawText: str
    publishedAt: Optional[str] = None


class RetellTask(BaseModel):
    prompt: str
    targetSpeakingSeconds: int = 45
    hints: list[str] = Field(default_factory=list)
    expectedContentPoints: list[str] = Field(default_factory=list)


class TeacherQuestion(BaseModel):
    id: str
    type: QuestionType
    question: str
    expectedIdeas: list[str] = Field(default_factory=list)
    usefulExpressionHint: Optional[str] = None


class UsefulLanguageItem(BaseModel):
    id: str
    category: UsefulLanguageCategory
    text: str
    meaning: str
    fromArticle: str
    whyUseful: str
    example: str
    reusePrompt: str


class IeltsTasks(BaseModel):
    listening: Optional[dict] = None
    reading: Optional[dict] = None
    writing: Optional[dict] = None
    speaking: Optional[dict] = None


class LessonProgress(BaseModel):
    stage: Literal["created", "retell", "questions", "useful_language", "review", "finished"] = "created"
    completedTaskIds: list[str] = Field(default_factory=list)
    answerCount: int = 0
    mistakeCount: int = 0
    learnedUsefulLanguageIds: list[str] = Field(default_factory=list)


class ArticleLesson(BaseModel):
    id: str
    userId: str
    source: ArticleSource
    level: str
    mainIdea: str
    keyPoints: list[str]
    retellTask: RetellTask
    questions: list[TeacherQuestion]
    usefulLanguage: list[UsefulLanguageItem]
    ieltsTasks: Optional[IeltsTasks] = None
    progress: LessonProgress = Field(default_factory=LessonProgress)


class ArticleLessonRequest(BaseModel):
    userId: str = "default-user"
    level: str = "B2-C1"
    articleUrl: Optional[str] = None
    articleText: Optional[str] = None
    mode: LessonMode = "speaking_first"
    includeIelts: bool = False


class SpeakingAnswerRequest(BaseModel):
    lessonId: str
    taskType: SpeakingTaskType
    taskId: str
    transcript: str
    attemptNumber: int = 1


class SpeakingTranscriptRequest(BaseModel):
    transcript: str
    attemptNumber: int = 1


class TeacherCorrection(BaseModel):
    score: int
    overallFeedback: str
    correctedAnswer: str
    naturalVersion: str
    advancedVersion: str
    mistakes: list[Mistake] = Field(default_factory=list)
    keyImprovements: list[str] = Field(default_factory=list)
    repeatPrompt: str
    nextAction: CorrectionNextAction


class LessonSummary(BaseModel):
    lessonId: str
    whatUserDidWell: list[str]
    repeatedMistakes: list[Mistake] = Field(default_factory=list)
    usefulExpressionsLearned: list[UsefulLanguageItem] = Field(default_factory=list)
    suggestedNextPractice: list[str] = Field(default_factory=list)
