export type Card = any;

const API_BASE = 'http://localhost:8000';

export async function startAgent(topic: string) {
  const res = await fetch(`${API_BASE}/agent/start`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, level: 'B2-C1', userId: 'default-user' }),
  });
  return res.json();
}

export async function submitAnswer(sessionId: string, cardId: string, userAnswer: string) {
  const res = await fetch(`${API_BASE}/agent/answer`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, cardId, userAnswer }),
  });
  return res.json();
}

export async function finishRound(sessionId: string) {
  const res = await fetch(`${API_BASE}/agent/finish`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId }),
  });
  return res.json();
}
