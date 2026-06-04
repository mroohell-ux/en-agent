export type CardType = 'Pattern' | 'Grammar' | 'Chunk';

export type LearningCard = {
  id: string;
  type: CardType;
  title: string;
  source?: { title: string; site: string; url: string };
  originalReference: string;
  extractedFromOriginal: string;
  target: string;
  referenceExample: string;
  chinesePrompt: string;
  expectedAnswer?: string;
  mustContain?: string;
};

export type Mistake = {
  type: 'grammar' | 'vocabulary' | 'expression' | 'naturalness' | 'structure' | 'logic' | string;
  original: string;
  correction: string;
  explanation?: string;
  explanationChinese?: string;
  reviewItem?: string;
};

export type NextAction = 'give_hint' | 'micro_lesson' | 'try_again' | 'follow_up_question' | 'next_card' | 'finish_round';

export type AnswerEvaluation = {
  score: number;
  status: string;
  targetUsed: boolean;
  targetUsageQuality: 'failed' | 'partial' | 'good' | 'excellent' | string;
  adviceChinese?: string;
  teacherResponseChinese?: string;
  mainTeachingPoint?: string | null;
  microLessonChinese?: string | null;
  retryPromptChinese?: string | null;
  followUpPromptChinese?: string | null;
  sentenceFrame?: string | null;
  correctedAnswer?: string;
  naturalVersion?: string;
  advancedVersion?: string;
  mistakes?: Mistake[];
  nextAction: NextAction;
};

export type StartResponse = { sessionId: string; cards: LearningCard[] };

export type RoundSummary = {
  practicedItems?: Array<{ cardTitle: string; target: string; score: number }>;
  whatUserDidWell?: string[];
  mistakesToRemember?: Array<{ mistake: string; correction: string; ruleChinese: string; example: string }>;
  weakItems?: string[];
  suggestedNextPractice?: string[];
};

export type ArticleSource = {
  title: string;
  url?: string | null;
  site?: string | null;
  rawText: string;
  publishedAt?: string | null;
};

export type RetellTask = {
  prompt: string;
  targetSpeakingSeconds: number;
  hints: string[];
  expectedContentPoints: string[];
};

export type TeacherQuestion = {
  id: string;
  type: 'comprehension' | 'explanation' | 'opinion' | 'personal_connection' | 'advanced_discussion';
  question: string;
  expectedIdeas: string[];
  usefulExpressionHint?: string | null;
};

export type UsefulLanguageItem = {
  id: string;
  category: 'expression' | 'vocabulary' | 'grammar' | 'sentence_pattern';
  text: string;
  meaning: string;
  fromArticle: string;
  whyUseful: string;
  example: string;
  reusePrompt: string;
};

export type ArticleLesson = {
  id: string;
  userId: string;
  source: ArticleSource;
  level: string;
  mainIdea: string;
  keyPoints: string[];
  retellTask: RetellTask;
  questions: TeacherQuestion[];
  usefulLanguage: UsefulLanguageItem[];
  ieltsTasks?: Record<string, unknown> | null;
  progress: {
    stage: string;
    completedTaskIds: string[];
    answerCount: number;
    mistakeCount: number;
    learnedUsefulLanguageIds: string[];
  };
};

export type TeacherCorrection = {
  score: number;
  overallFeedback: string;
  correctedAnswer: string;
  naturalVersion: string;
  advancedVersion: string;
  mistakes: Mistake[];
  keyImprovements: string[];
  repeatPrompt: string;
  nextAction: string;
};

export type LessonSummary = {
  lessonId: string;
  whatUserDidWell: string[];
  repeatedMistakes: Mistake[];
  usefulExpressionsLearned: UsefulLanguageItem[];
  suggestedNextPractice: string[];
};

const API_BASE = (import.meta as ImportMeta & { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ?? 'http://localhost:8000';

export type ApiErrorDetail = { step?: string; rootCause?: string };

export class ApiRequestError extends Error {
  step?: string;
  rootCause: string;

  constructor(message: string, detail: ApiErrorDetail = {}) {
    super(message);
    this.name = 'ApiRequestError';
    this.step = detail.step;
    this.rootCause = detail.rootCause || message;
  }
}

function isErrorDetail(value: unknown): value is ApiErrorDetail {
  if (!value || typeof value !== 'object') return false;
  const detail = value as Record<string, unknown>;
  return typeof detail.step === 'string' || typeof detail.rootCause === 'string';
}

async function readErrorDetail(res: Response): Promise<ApiErrorDetail> {
  try {
    const payload = await res.json();
    const detail = payload?.detail;
    if (isErrorDetail(detail)) return { step: detail.step, rootCause: detail.rootCause || `Request failed with status ${res.status}.` };
    if (typeof detail === 'string') return { rootCause: detail };
  } catch {
    // Fall back below.
  }
  return { rootCause: `Request failed with status ${res.status}.` };
}

async function postJson<TResponse, TBody extends Record<string, unknown>>(path: string, body: TBody): Promise<TResponse> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiRequestError(`Request failed (${res.status}) for ${path}`, await readErrorDetail(res));
  return res.json();
}

async function getJson<TResponse>(path: string): Promise<TResponse> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new ApiRequestError(`Request failed (${res.status}) for ${path}`, await readErrorDetail(res));
  return res.json();
}

export function startAgent(topic: string) {
  return postJson<StartResponse, Record<string, unknown>>('/agent/start', { topic, userId: 'default-user' });
}

export function answer(payload: { sessionId: string; cardId: string; userAnswer: string }) {
  return postJson<AnswerEvaluation, Record<string, unknown>>('/agent/answer', payload);
}

export function finishRound(sessionId: string) {
  return postJson<RoundSummary, Record<string, unknown>>('/agent/finish', { sessionId });
}

export function listLessons(userId = 'default-user') {
  return getJson<ArticleLesson[]>(`/lessons?userId=${encodeURIComponent(userId)}`);
}

export function createArticleLesson(payload: { articleText?: string; articleUrl?: string; level: string; includeIelts: boolean }) {
  return postJson<ArticleLesson, Record<string, unknown>>('/lessons/from-article', {
    userId: 'default-user',
    mode: 'speaking_first',
    ...payload,
  });
}

export function submitRetell(lessonId: string, transcript: string, attemptNumber = 1) {
  return postJson<TeacherCorrection, Record<string, unknown>>(`/lessons/${lessonId}/retell`, { transcript, attemptNumber });
}

export function submitQuestionAnswer(lessonId: string, questionId: string, transcript: string, attemptNumber = 1) {
  return postJson<TeacherCorrection, Record<string, unknown>>(`/lessons/${lessonId}/questions/${questionId}/answer`, { transcript, attemptNumber });
}

export function submitUsefulLanguagePractice(lessonId: string, itemId: string, transcript: string, attemptNumber = 1) {
  return postJson<TeacherCorrection, Record<string, unknown>>(`/lessons/${lessonId}/useful-language/${itemId}/practice`, { transcript, attemptNumber });
}

export function finishLesson(lessonId: string) {
  return postJson<LessonSummary, Record<string, unknown>>(`/lessons/${lessonId}/finish`, {});
}
