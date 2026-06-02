import type { RoundSummary } from '../api/agentClient';

type Props = {
  summary: RoundSummary;
  onStartAnotherRound: () => void;
};

export default function RoundSummaryCard({ summary, onStartAnotherRound }: Props) {
  return (
    <article className="summary-card">
      <header className="card-header">
        <div>
          <p className="eyebrow">Round complete</p>
          <h2>Round Summary</h2>
        </div>
        <button className="primary-button" onClick={onStartAnotherRound}>Start another round</button>
      </header>

      <section>
        <h3>Practiced items</h3>
        <ul className="summary-list">
          {(summary.practicedItems ?? []).map((item) => (
            <li key={`${item.cardTitle}-${item.target}`}>
              <strong>{item.cardTitle}</strong>
              <p className="muted">{item.target} · {item.score}/100</p>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>What you did well</h3>
        <ul className="summary-list">
          {(summary.whatUserDidWell ?? []).map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>

      <section>
        <h3>Mistakes to remember</h3>
        <ul className="summary-list">
          {(summary.mistakesToRemember ?? []).map((item) => (
            <li key={`${item.mistake}-${item.correction}`}>
              <strong>{item.mistake} → {item.correction}</strong>
              <p>{item.ruleChinese}</p>
              <p className="muted">{item.example}</p>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Suggested next practice</h3>
        <ul className="summary-list">
          {(summary.suggestedNextPractice ?? []).map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
    </article>
  );
}
