import { useState } from 'react';
import { startAgent, type LearningCard } from './api/agentClient';
import StudySession from './components/StudySession';
import './styles.css';

export default function App() {
  const [topic, setTopic] = useState('random');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [cards, setCards] = useState<LearningCard[]>([]);
  const [error, setError] = useState('');

  const generate = async () => {
    setLoading(true);
    setError('');

    try {
      const data = await startAgent(topic);
      setCards(data.cards);
      setSessionId(data.sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start a new round.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <section className="hero" aria-label="Start learning round">
        <div className="hero-copy">
          <p className="eyebrow">Premium transfer practice</p>
          <h1>Timescape English</h1>
          <p>
            Practice one reusable English pattern at a time. Each card behaves like a mini lesson: answer,
            get teacher feedback, retry with a hint, then move on only when you are ready.
          </p>
        </div>

        <div className="start-panel">
          <input
            className="topic-input"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="random, technology, culture..."
            aria-label="Practice topic"
          />
          <button className="primary-button" onClick={generate} disabled={loading}>
            {loading ? 'Preparing cards…' : cards.length ? 'Start another round' : 'Generate cards'}
          </button>
        </div>
      </section>

      {loading && (
        <section className="loading-card" aria-live="polite">
          <p>Searching useful material with Tavily…</p>
          <p>Extracting reusable English…</p>
          <p>Preparing Chinese transfer prompts…</p>
        </section>
      )}

      {error && <section className="loading-card">{error}</section>}

      {sessionId && cards.length > 0 ? (
        <StudySession key={sessionId} sessionId={sessionId} cards={cards} onStartAnotherRound={generate} />
      ) : (
        !loading && <section className="empty-state">Generate a round to reveal the first stacked learning card.</section>
      )}
    </main>
  );
}
