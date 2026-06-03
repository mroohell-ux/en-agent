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

export type SourceArticle = {
  title: string;
  url: string;
  content: string;
  snippet: string;
  site: string;
};

export type StartResponse = {
  sessionId: string;
  cards: LearningCard[];
  sourceArticles?: SourceArticle[];
};

export type RoundSummary = {
  practicedItems?: Array<{ cardTitle: string; target: string; score: number }>;
  whatUserDidWell?: string[];
  mistakesToRemember?: Array<{ mistake: string; correction: string; ruleChinese: string; example: string }>;
  weakItems?: string[];
  suggestedNextPractice?: string[];
};

const API_BASE = (import.meta as ImportMeta & { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ?? 'http://localhost:8000';
const REQUEST_LOG_STYLE = 'color: #dc2626; font-weight: 900;';
const RESPONSE_LOG_STYLE = 'color: #16a34a; font-weight: 800;';
const ERROR_LOG_STYLE = 'color: #b91c1c; font-weight: 900;';

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
  const url = `${API_BASE}${path}`;
  const requestPayload = JSON.stringify(body);

  console.debug('%c[agent-api] REQUEST sending', REQUEST_LOG_STYLE, {
    method: 'POST',
    path,
    url,
    headers: { 'Content-Type': 'application/json' },
    payload: body,
    serializedPayload: requestPayload,
  });

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: requestPayload,
  });

  if (!res.ok) {
    const detail = await readErrorDetail(res);
    console.error('%c[agent-api] REQUEST failed', ERROR_LOG_STYLE, {
      method: 'POST',
      path,
      url,
      status: res.status,
      statusText: res.statusText,
      requestPayload: body,
      errorDetail: detail,
    });
    throw new ApiRequestError(`Request failed (${res.status}) for ${path}`, detail);
  }

  const responsePayload = (await res.json()) as TResponse;
  console.debug('%c[agent-api] RESPONSE received', RESPONSE_LOG_STYLE, {
    method: 'POST',
    path,
    url,
    status: res.status,
    statusText: res.statusText,
    requestPayload: body,
    responsePayload,
  });

  return responsePayload;
}

export function startAgent(topic: string) {
  return postJson<StartResponse, Record<string, unknown>>('/agent/start', {
    topic,
    userId: 'default-user',
  });
}

export function answer(payload: { sessionId: string; cardId: string; userAnswer: string }) {
  return postJson<AnswerEvaluation, Record<string, unknown>>('/agent/answer', payload);
}

export function finishRound(sessionId: string) {
  return postJson<RoundSummary, Record<string, unknown>>('/agent/finish', { sessionId });
}
