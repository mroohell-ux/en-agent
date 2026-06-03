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

function statusLabel(state: CardInteractionState) {
  const evaluation = state.latestEvaluation;

  if (!evaluation) {
    if (state.status === 'not_started') return 'Not started';
    return 'Ready';
  }

  if (!evaluation.targetUsed) return 'Target missing';
  if (state.status === 'passed') return 'Good transfer';
  return 'Needs retry';
}

export default function CardStack(props: Props) {
  const { cards, cardStates, activeIndex, onSelectCard } = props;
  const activeCard = cards[activeIndex];
  const activeState = cardStates[activeCard.id];
  const inactiveCards = cards
    .map((card, index) => ({ card, index, state: cardStates[card.id] }))
    .filter(({ index }) => index !== activeIndex);

  return (
    <div className="card-stack">
      <LearningCardView
        key={activeCard.id}
        card={activeCard}
        state={activeState}
        index={activeIndex}
        total={cards.length}
        isSubmitting={props.submittingCardId === activeCard.id}
        hasNextCard={activeIndex < cards.length - 1}
        onAnswerChange={props.onAnswerChange}
        onSubmit={props.onSubmit}
        onNextCard={props.onNextCard}
        onFinish={props.onFinish}
      />

      {inactiveCards.length > 0 && (
        <div className="collapsed-card-stack" aria-label="Other cards in this round">
          {inactiveCards.map(({ card, index, state }) => {
            const canReview = index <= activeIndex || state.status === 'passed';

            return (
              <button
                key={card.id}
                className={`stack-preview ${canReview ? '' : 'locked'}`}
                onClick={() => canReview && onSelectCard(index)}
                disabled={!canReview}
              >
                <span>
                  <span className="preview-card-number">Card {index + 1}</span>
                  <span className="badge type">{card.type}</span>
                  <div className="preview-title">{card.title || card.target}</div>
                  <div className="preview-meta">{card.target}</div>
                </span>
                <span className={`badge status ${state.status === 'passed' ? 'passed' : ''}`}>
                  {statusLabel(state)}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
