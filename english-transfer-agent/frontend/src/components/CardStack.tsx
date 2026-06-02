import type { LearningCard } from '../api/agentClient';
import LearningCardView from './LearningCard';
import type { CardInteractionState } from './StudySession';

type Props = {
  cards: LearningCard[];
  cardStates: Record<string, CardInteractionState>;
  activeIndex: number;
  submittingCardId: string | null;
  onAnswerChange: (cardId: string, answer: string) => void;
  onSubmit: (cardId: string) => void;
  onSelectCard: (index: number) => void;
  onNextCard: () => void;
  onFinish: () => void;
};

function statusLabel(status: CardInteractionState['status']) {
  if (status === 'passed') return 'Passed';
  if (status === 'retrying' || status === 'feedback' || status === 'answering') return 'In progress';
  return 'Not started';
}

function bestScore(state: CardInteractionState) {
  const scores = state.attempts.map((attempt) => attempt.evaluation.score).filter((score) => Number.isFinite(score));
  return scores.length ? Math.max(...scores) : undefined;
}

export default function CardStack(props: Props) {
  const { cards, cardStates, activeIndex, onSelectCard } = props;

  return (
    <div className="card-stack">
      {cards.map((card, index) => {
        const state = cardStates[card.id];
        const isActive = index === activeIndex;
        const canReview = index <= activeIndex || state.status === 'passed';
        const score = bestScore(state);

        if (isActive) {
          return (
            <LearningCardView
              key={card.id}
              card={card}
              state={state}
              index={index}
              total={cards.length}
              isSubmitting={props.submittingCardId === card.id}
              hasNextCard={index < cards.length - 1}
              onAnswerChange={props.onAnswerChange}
              onSubmit={props.onSubmit}
              onNextCard={props.onNextCard}
              onFinish={props.onFinish}
            />
          );
        }

        return (
          <button
            key={card.id}
            className={`stack-preview ${canReview ? '' : 'locked'}`}
            onClick={() => canReview && onSelectCard(index)}
            disabled={!canReview}
            style={{ transform: `translateY(${Math.min(index, 3) * -2}px)` }}
          >
            <span>
              <span className="badge type">{card.type}</span>
              <div className="preview-title">{card.title || card.target}</div>
              <div className="preview-meta">{card.target}</div>
            </span>
            <span className={`badge status ${state.status === 'passed' ? 'passed' : ''}`}>
              {score ? `${score}/100 · ` : ''}{statusLabel(state.status)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
