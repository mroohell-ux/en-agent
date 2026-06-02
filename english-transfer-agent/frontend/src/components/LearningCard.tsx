import type { LearningCard } from '../api/agentClient';
import AttemptHistory from './AttemptHistory';
import ReferenceReveal from './ReferenceReveal';
import RetryBox from './RetryBox';
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

function statusLabel(status: CardInteractionState['status']) {
  if (status === 'passed') return 'Passed';
  if (status === 'not_started') return 'Not started';
  return 'In progress';
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

  return (
    <article className="learning-card">
      <header className="card-header">
        <div className="header-left">
          <span className="badge type">{card.type}</span>
          <span className="card-count">Card {index + 1} / {total}</span>
        </div>
        <div className="badge-row">
          <span className={`badge status ${isPassed ? 'passed' : ''}`}>{statusLabel(state.status)}</span>
          {latestEvaluation && <span className="badge score">{latestEvaluation.score}/100</span>}
        </div>
      </header>

      <section className="teacher-prompt">
        <p className="section-label">Teacher asks</p>
        <p className="prompt-text">{state.currentPromptChinese}</p>
      </section>

      {showAnswerBox && (
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

      {latestEvaluation && <TeacherFeedback evaluation={latestEvaluation} />}
      {latestEvaluation && <RetryBox evaluation={latestEvaluation} />}

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
