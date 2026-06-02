import type { CardAttempt } from './StudySession';

type Props = {
  attempts: CardAttempt[];
};

export default function AttemptHistory({ attempts }: Props) {
  if (!attempts.length) return null;

  return (
    <details className="reveal">
      <summary>Attempt history</summary>
      {attempts.map((attempt) => {
        const mistake = attempt.evaluation.mistakes?.[0];
        const goodTransfer = attempt.evaluation.targetUsed && !mistake;

        return (
          <div className="history-item" key={attempt.attemptNumber}>
            <div className="history-top">
              <span>Attempt {attempt.attemptNumber} · {attempt.evaluation.score}/100</span>
              <span className="muted">{attempt.evaluation.status}</span>
            </div>
            <p className="muted">Prompt: {attempt.promptChinese}</p>
            <p className="answer-line">{attempt.userAnswer}</p>
            {mistake ? (
              <p>Issue: {mistake.original} → {mistake.correction}</p>
            ) : (
              goodTransfer && <p>Good transfer.</p>
            )}
          </div>
        );
      })}
    </details>
  );
}
