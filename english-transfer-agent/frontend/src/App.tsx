import { useState } from 'react';
import { ApiRequestError, startAgent, type LearningCard } from './api/agentClient';
import StudySession from './components/StudySession';
import './styles.css';

type UserFacingError = {
  step: string;
  rootCause: string;
};

function describeError(err: unknown, fallbackStep: string): UserFacingError {
  if (err instanceof ApiRequestError) {
    return {
      step: err.step || fallbackStep,
      rootCause: err.rootCause,
    };
  }

  if (err instanceof TypeError) {
    return {
      step: 'Connect to backend',
      rootCause: 'The frontend could not reach the API server. Check that the backend is running and CORS/API URL settings are correct.',
    };
  }

  if (err instanceof Error) {
    return { step: fallbackStep, rootCause: err.message };
  }

  return { step: fallbackStep, rootCause: 'Something unexpected happened.' };
}

export default function App() {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [cards, setCards] = useState<LearningCard[]>([]);
  const [error, setError] = useState<UserFacingError | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await startAgent(topic.trim() || 'random');
      setCards(data.cards);
      setSessionId(data.sessionId);
    } catch (err) {
      setError(describeError(err, 'Build practice round'));
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
          <label className="topic-label" htmlFor="practice-topic">Practice topic</label>
          <select
            id="practice-topic"
            className="topic-input topic-select"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            aria-describedby="practice-topic-help"
          >
            <option value="">Surprise me</option>
            <option value="technology">Technology</option>
            <option value="culture">Culture</option>
            <option value="science">Science</option>
            <option value="psychology">Psychology</option>
            <option value="lifestyle">Lifestyle</option>
          </select>
          <p className="topic-help" id="practice-topic-help">
            This chooses the source material for your practice cards. “Surprise me” picks a random topic.
          </p>
          <button className="primary-button" onClick={generate} disabled={loading}>
            {loading ? 'Preparing cards…' : cards.length ? 'Start another round' : 'Generate cards'}
          </button>
        </div>
      </section>

      {loading && (
        <section className="loading-card backend-status" aria-live="polite">
          <p className="loading-title">Building your practice round…</p>
          <p className="loading-note">The backend is doing a few teacher tasks for you now:</p>
          <ol className="loading-steps">
            <li>Finding a real-world English article that ordinary educated readers would actually read.</li>
            <li>Choosing reusable phrases or grammar patterns worth practicing.</li>
            <li>Writing Chinese-first prompt cards so you can transfer the pattern yourself.</li>
            <li>Preparing teacher feedback rules for your first answer and retry.</li>
          </ol>
        </section>
      )}

      {error && (
        <section className="loading-card error-card" role="alert">
          <p className="error-title">Could not finish this step.</p>
          <p><strong>Step:</strong> {error.step}</p>
          <p><strong>Root cause:</strong> {error.rootCause}</p>
        </section>
      )}

      {sessionId && cards.length > 0 ? (
        <StudySession key={sessionId} sessionId={sessionId} cards={cards} onStartAnotherRound={generate} />
      ) : (
        !loading && <section className="empty-state">Generate a round to reveal the first stacked learning card.</section>
      )}
    </main>
  );
}
