import { useMemo, useState } from 'react';
import { answer, finishRound, type AnswerEvaluation, type LearningCard, type NextAction, type RoundSummary } from '../api/agentClient';
import CardStack from './CardStack';
import RoundSummaryCard from './RoundSummaryCard';

export type CardStatus = 'not_started' | 'answering' | 'feedback' | 'retrying' | 'passed';

export type CardAttempt = {
  attemptNumber: number;
  promptChinese: string;
  userAnswer: string;
  evaluation: AnswerEvaluation;
};

export type CardInteractionState = {
  cardId: string;
  status: CardStatus;
  currentPromptChinese: string;
  currentAnswer: string;
  attempts: CardAttempt[];
  latestEvaluation?: AnswerEvaluation;
};

type Props = {
  sessionId: string;
  cards: LearningCard[];
  onStartAnotherRound: () => void;
};

export function getStatusFromNextAction(nextAction: NextAction): CardStatus {
  if (
    nextAction === 'give_hint' ||
    nextAction === 'micro_lesson' ||
    nextAction === 'try_again' ||
    nextAction === 'follow_up_question'
  ) {
    return 'retrying';
  }

  if (nextAction === 'next_card' || nextAction === 'finish_round') {
    return 'passed';
  }

  return 'feedback';
}

function createInitialCardStates(cards: LearningCard[]) {
  return cards.reduce<Record<string, CardInteractionState>>((acc, card, index) => {
    acc[card.id] = {
      cardId: card.id,
      status: index === 0 ? 'answering' : 'not_started',
      currentPromptChinese: card.chinesePrompt,
      currentAnswer: '',
      attempts: [],
    };
    return acc;
  }, {});
}

export default function StudySession({ sessionId, cards, onStartAnotherRound }: Props) {
  const [cardStates, setCardStates] = useState(() => createInitialCardStates(cards));
  const [activeIndex, setActiveIndex] = useState(0);
  const [submittingCardId, setSubmittingCardId] = useState<string | null>(null);
  const [finishing, setFinishing] = useState(false);
  const [summary, setSummary] = useState<RoundSummary | null>(null);
  const [error, setError] = useState('');

  const activeCard = cards[activeIndex];
  const allPassed = useMemo(() => cards.length > 0 && cards.every((card) => cardStates[card.id]?.status === 'passed'), [cards, cardStates]);
  const shouldOfferFinish = allPassed || cards.some((card) => cardStates[card.id]?.latestEvaluation?.nextAction === 'finish_round');

  const updateCardAnswer = (cardId: string, currentAnswer: string) => {
    setCardStates((previous) => ({
      ...previous,
      [cardId]: {
        ...previous[cardId],
        status: previous[cardId].attempts.length ? previous[cardId].status : 'answering',
        currentAnswer,
      },
    }));
  };

  const submitAnswer = async (cardId: string) => {
    const cardState = cardStates[cardId];
    const userAnswer = cardState.currentAnswer.trim();

    if (!userAnswer) return;

    setSubmittingCardId(cardId);
    setError('');

    try {
      const evaluation = await answer({ sessionId, cardId, userAnswer });
      const attempt: CardAttempt = {
        attemptNumber: cardState.attempts.length + 1,
        promptChinese: cardState.currentPromptChinese,
        userAnswer,
        evaluation,
      };
      const nextPrompt =
        evaluation.retryPromptChinese || evaluation.followUpPromptChinese || cardState.currentPromptChinese;

      setCardStates((previous) => ({
        ...previous,
        [cardId]: {
          ...previous[cardId],
          attempts: [...previous[cardId].attempts, attempt],
          latestEvaluation: evaluation,
          currentAnswer: '',
          currentPromptChinese: nextPrompt,
          status: getStatusFromNextAction(evaluation.nextAction),
        },
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not evaluate this answer.');
    } finally {
      setSubmittingCardId(null);
    }
  };

  const goToCard = (index: number) => {
    if (index < 0 || index >= cards.length) return;
    const requested = cards[index];
    const requestedState = cardStates[requested.id];

    if (index <= activeIndex || requestedState.status === 'passed') {
      setActiveIndex(index);
    }
  };

  const goNextCard = () => {
    const nextIndex = Math.min(activeIndex + 1, cards.length - 1);
    const nextCard = cards[nextIndex];

    setCardStates((previous) => ({
      ...previous,
      [nextCard.id]: {
        ...previous[nextCard.id],
        status: previous[nextCard.id].status === 'not_started' ? 'answering' : previous[nextCard.id].status,
      },
    }));
    setActiveIndex(nextIndex);
  };

  const finish = async () => {
    setFinishing(true);
    setError('');

    try {
      setSummary(await finishRound(sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not finish this round.');
    } finally {
      setFinishing(false);
    }
  };

  if (summary) {
    return <RoundSummaryCard summary={summary} onStartAnotherRound={onStartAnotherRound} />;
  }

  return (
    <section aria-label="Stacked learning cards">
      {error && <div className="loading-card">{error}</div>}
      <CardStack
        cards={cards}
        cardStates={cardStates}
        activeIndex={activeIndex}
        submittingCardId={submittingCardId}
        onAnswerChange={updateCardAnswer}
        onSubmit={submitAnswer}
        onSelectCard={goToCard}
        onNextCard={goNextCard}
        onFinish={finish}
      />
      {shouldOfferFinish && activeCard && activeCard.id !== cards[cards.length - 1].id && (
        <div className="finish-panel">
          <button className="secondary-button" onClick={finish} disabled={finishing}>
            {finishing ? 'Finishing…' : 'Finish Round'}
          </button>
        </div>
      )}
    </section>
  );
}
