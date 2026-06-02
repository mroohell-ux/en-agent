export type CardType = 'Pattern' | 'Grammar' | 'Chunk';

export type LearningCard = {
  id: string;
  type: CardType;
  title: string;
  source?: {
    title: string;
    site: string;
    url: string;
  };
  originalReference: string;
  extractedFromOriginal: string;
  target: string;
  referenceExample: string;
  chinesePrompt: string;
  expectedAnswer?: string;
  mustContain?: string;
};

export type Mistake = {
  type: 'pattern' | 'grammar' | 'naturalness' | 'word_choice' | 'structure' | string;
  original: string;
  correction: string;
  explanationChinese: string;
  reviewItem?: string;
};

export type NextAction =
  | 'give_hint'
  | 'micro_lesson'
  | 'try_again'
  | 'follow_up_question'
  | 'next_card'
  | 'finish_round';

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

export type StartResponse = {
  sessionId: string;
  cards: LearningCard[];
};

export type RoundSummary = {
  practicedItems?: Array<{ cardTitle: string; target: string; score: number }>;
  whatUserDidWell?: string[];
  mistakesToRemember?: Array<{ mistake: string; correction: string; ruleChinese: string; example: string }>;
  weakItems?: string[];
  suggestedNextPractice?: string[];
};

const API_BASE = (import.meta as ImportMeta & { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ?? 'http://localhost:8000';

export type ApiErrorDetail = {
  step?: string;
  rootCause?: string;
};

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

    if (isErrorDetail(detail)) {
      return {
        step: detail.step,
        rootCause: detail.rootCause || `Request failed with status ${res.status}.`,
      };
    }

    if (typeof detail === 'string') {
      return { rootCause: detail };
    }
  } catch {
    // Fall back to the generic HTTP message below when the response is not JSON.
  }

  return { rootCause: `Request failed with status ${res.status}.` };
}

async function postJson<TResponse, TBody extends Record<string, unknown>>(path: string, body: TBody): Promise<TResponse> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const detail = await readErrorDetail(res);
    throw new ApiRequestError(`Request failed (${res.status}) for ${path}`, detail);
  }

  return res.json();
}

export function startAgent(topic: string) {
  return postJson<StartResponse, Record<string, unknown>>('/agent/start', {
    topic,
    level: 'B2-C1',
    userId: 'default-user',
  });
}

export function answer(payload: { sessionId: string; cardId: string; userAnswer: string }) {
  return postJson<AnswerEvaluation, Record<string, unknown>>('/agent/answer', payload);
}

export function finishRound(sessionId: string) {
  return postJson<RoundSummary, Record<string, unknown>>('/agent/finish', { sessionId });
}
