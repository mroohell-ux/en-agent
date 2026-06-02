import type { LearningCard } from '../api/agentClient';

type Props = {
  card: LearningCard;
};

export default function ReferenceReveal({ card }: Props) {
  return (
    <details className="reveal">
      <summary>Show reference and target</summary>
      <div className="history-item">
        <div className="kicker">Original reference</div>
        <p>{card.originalReference}</p>
      </div>
      <div className="history-item">
        <div className="kicker">Extracted from original</div>
        <p>{card.extractedFromOriginal}</p>
      </div>
      <div className="history-item">
        <div className="kicker">Target</div>
        <p className="answer-line">{card.target}</p>
      </div>
      <div className="history-item">
        <div className="kicker">Reference example</div>
        <p>{card.referenceExample}</p>
      </div>
    </details>
  );
}
