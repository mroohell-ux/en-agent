import { useEffect, useState } from 'react';
import { ApiRequestError, startAgent, type LearningCard } from './api/agentClient';
import StudySession from './components/StudySession';
import './styles.css';

type UserFacingError = {
  step: string;
  rootCause: string;
};

type BackendActivity = {
  label: string;
  hint: string;
};

type ActivityHistoryItem = {
  id: string;
  status: 'started' | 'completed' | 'failed';
  text: string;
};

const BACKEND_ACTIVITIES: BackendActivity[] = [
  {
    label: 'Search trusted article sources',
    hint: 'Tavily is looking inside preset real-world publications and skipping learner-level sites.',
  },
  {
    label: 'Read the article material',
    hint: 'The backend is checking returned article text for useful, reusable English.',
  },
  {
    label: 'Extract transfer targets',
    hint: 'It is choosing phrases, patterns, or grammar that can become practice cards.',
  },
  {
    label: 'Write Chinese-first cards',
    hint: 'It is turning those targets into prompts where you produce the English yourself.',
  },
  {
    label: 'Prepare teacher checks',
    hint: 'It is preparing what to look for in your answer, retry, and follow-up.',
  },
];

function topicLabel(topic: string) {
  return topic || 'surprise topic';
}

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
  const [activityIndex, setActivityIndex] = useState(0);
  const [activityHistory, setActivityHistory] = useState<ActivityHistoryItem[]>([]);

  useEffect(() => {
    if (!loading) return undefined;

    const timer = window.setInterval(() => {
      setActivityIndex((current) => Math.min(current + 1, BACKEND_ACTIVITIES.length - 1));
    }, 1800);

    return () => window.clearInterval(timer);
  }, [loading]);

  const addActivityHistory = (item: Omit<ActivityHistoryItem, 'id'>) => {
    setActivityHistory((previous) => [
      { ...item, id: `${Date.now()}-${item.status}-${previous.length}` },
      ...previous,
    ].slice(0, 4));
  };

  const generate = async () => {
    const selectedTopic = topic.trim() || 'random';
    setLoading(true);
    setActivityIndex(0);
    setError(null);
    addActivityHistory({ status: 'started', text: `Started building cards for ${topicLabel(topic)}.` });

    try {
      const data = await startAgent(selectedTopic);
      setCards(data.cards);
      setSessionId(data.sessionId);
      addActivityHistory({ status: 'completed', text: `Built ${data.cards.length} cards for ${topicLabel(topic)}.` });
    } catch (err) {
      const describedError = describeError(err, 'Build practice round');
      setError(describedError);
      addActivityHistory({ status: 'failed', text: `${describedError.step} failed: ${describedError.rootCause}` });
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
          <p className="loading-note">Live hint: {BACKEND_ACTIVITIES[activityIndex].hint}</p>
          <ol className="loading-steps live-steps">
            {BACKEND_ACTIVITIES.map((activity, index) => {
              const status = index < activityIndex ? 'done' : index === activityIndex ? 'active' : 'waiting';

              return (
                <li className={`live-step ${status}`} key={activity.label}>
                  <span className="step-status">{status === 'done' ? 'Done' : status === 'active' ? 'Now' : 'Next'}</span>
                  <span>{activity.label}</span>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {activityHistory.length > 0 && !loading && (
        <section className="loading-card activity-history" aria-label="Backend activity history">
          <p className="loading-title">Recent backend activity</p>
          {activityHistory.map((item) => (
            <p className={`activity-row ${item.status}`} key={item.id}>
              <span className="step-status">{item.status}</span>
              <span>{item.text}</span>
            </p>
          ))}
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
