import type { LearningCard } from '../api/agentClient';
import AttemptHistory from './AttemptHistory';
import ReferenceReveal from './ReferenceReveal';
import type { CardInteractionState } from './StudySession';
import TeacherFeedback from './TeacherFeedback';

type Props = {
  card: LearningCard;
  state: CardInteractionState;
  index: number;
  total: number;
  isSubmitting: boolean;
  hasNextCard: boolean;
  onAnswerChange: (cardId: string, answer: string) => void;
  onSubmit: (cardId: string) => void;
  onNextCard: () => void;
  onFinish: () => void;
};

function statusLabel(state: CardInteractionState) {
  const evaluation = state.latestEvaluation;

  if (!evaluation) {
    if (state.status === 'passed') return 'Good transfer';
    if (state.status === 'not_started') return 'Not started';
    return 'Ready';
  }

  if (!evaluation.targetUsed) return 'Target missing';
  if (evaluation.nextAction === 'try_again' || evaluation.nextAction === 'micro_lesson' || evaluation.nextAction === 'give_hint') return 'Needs retry';
  if (evaluation.nextAction === 'follow_up_question') return 'Needs retry';
  if (evaluation.targetUsageQuality === 'excellent' || evaluation.targetUsageQuality === 'good') return 'Good transfer';
  return 'Needs retry';
}

function submitLabel(state: CardInteractionState) {
  const nextAction = state.latestEvaluation?.nextAction;

  if (!state.attempts.length) return 'Submit answer';
  if (nextAction === 'micro_lesson') return 'Try again';
  return 'Submit again';
}

function canRetry(state: CardInteractionState) {
  return (
    state.latestEvaluation?.nextAction === 'give_hint' ||
    state.latestEvaluation?.nextAction === 'micro_lesson' ||
    state.latestEvaluation?.nextAction === 'try_again' ||
    state.latestEvaluation?.nextAction === 'follow_up_question' ||
    !state.latestEvaluation
  );
}

export default function LearningCardView({
  card,
  state,
  index,
  total,
  isSubmitting,
  hasNextCard,
  onAnswerChange,
  onSubmit,
  onNextCard,
  onFinish,
}: Props) {
  const latestEvaluation = state.latestEvaluation;
  const isPassed = state.status === 'passed';
  const nextAction = latestEvaluation?.nextAction;
  const showAnswerBox = canRetry(state) && !isPassed;
  const showInitialAnswerBox = showAnswerBox && !latestEvaluation;
  const showRetryAnswerBox = showAnswerBox && Boolean(latestEvaluation);
  const latestAttempt = state.attempts[state.attempts.length - 1];
  const retryPrompt = latestEvaluation?.retryPromptChinese || latestEvaluation?.followUpPromptChinese || state.currentPromptChinese;

  return (
    <article className="learning-card">
      <header className="card-header">
        <div className="header-left">
          <span className="badge type">{card.type}</span>
          <span className="card-count">Card {index + 1} / {total}</span>
        </div>
        <div className="badge-row">
          <span className={`badge status ${isPassed ? 'passed' : ''}`}>{statusLabel(state)}</span>
          {latestEvaluation && <span className="score-chip">Score {latestEvaluation.score}/100</span>}
        </div>
      </header>

      <section className="teacher-prompt">
        <div className="prompt-topline">
          <p className="section-label">Teacher asks</p>
          <span className="target-pill">Target: {card.target}</span>
        </div>
        <p className="prompt-text">{card.chinesePrompt}</p>
      </section>

      {showInitialAnswerBox && (
        <section className="answer-area" aria-label="Answer this card">
          <textarea
            value={state.currentAnswer}
            onChange={(event) => onAnswerChange(card.id, event.target.value)}
            placeholder="Type your English answer…"
          />
          <button
            className="primary-button"
            onClick={() => onSubmit(card.id)}
            disabled={isSubmitting || !state.currentAnswer.trim()}
          >
            {isSubmitting ? 'Evaluating…' : submitLabel(state)}
          </button>
        </section>
      )}

      {latestEvaluation && latestAttempt && (
        <TeacherFeedback evaluation={latestEvaluation} target={card.target} userAnswer={latestAttempt.userAnswer} />
      )}

      {showRetryAnswerBox && (
        <section className="retry-area" aria-label="Try again or answer the follow-up">
          <div className="retry-copy">
            <div className="kicker">Try again</div>
            {retryPrompt && <p>{retryPrompt}</p>}
            {latestEvaluation?.sentenceFrame && <div className="frame">Sentence frame: {latestEvaluation.sentenceFrame}</div>}
          </div>
          <textarea
            value={state.currentAnswer}
            onChange={(event) => onAnswerChange(card.id, event.target.value)}
            placeholder="Try your revised English answer…"
          />
          <button
            className="primary-button"
            onClick={() => onSubmit(card.id)}
            disabled={isSubmitting || !state.currentAnswer.trim()}
          >
            {isSubmitting ? 'Evaluating…' : 'Submit again'}
          </button>
        </section>
      )}

      {nextAction === 'next_card' && hasNextCard && (
        <div className="finish-panel">
          <button className="secondary-button" onClick={onNextCard}>Next Card</button>
        </div>
      )}
      {nextAction === 'next_card' && !hasNextCard && (
        <div className="finish-panel">
          <button className="secondary-button" onClick={onFinish}>Finish Round</button>
        </div>
      )}
      {nextAction === 'finish_round' && (
        <div className="finish-panel">
          <button className="secondary-button" onClick={onFinish}>Finish Round</button>
        </div>
      )}

      <AttemptHistory attempts={state.attempts} />
      {state.attempts.length > 0 && <ReferenceReveal card={card} />}
    </article>
  );
}
