import { useState } from 'react';
import { finishRound, startAgent, submitAnswer } from './api/agentClient';
import StackedLearningCards from './components/StackedLearningCards';
import RoundSummary from './components/RoundSummary';

export default function App() {
  const [topic, setTopic] = useState('random');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [cards, setCards] = useState<any[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [summary, setSummary] = useState<any>(null);

  const generate = async () => {
    setLoading(true);
    const data = await startAgent(topic);
    setCards(data.cards); setSessionId(data.sessionId); setActiveIndex(0); setSummary(null); setLoading(false);
  };

  const onSubmit = async (cardId: string, answer: string) => submitAnswer(sessionId, cardId, answer);
  const onAdvance = () => setActiveIndex((i) => Math.min(i + 1, cards.length - 1));
  const onFinish = async () => setSummary(await finishRound(sessionId));

  return <main style={{ maxWidth: 520, margin: '0 auto', padding: 16 }}>
    <h1>Timescape English</h1><p>Reference → Transfer</p>
    <input value={topic} onChange={e=>setTopic(e.target.value)} placeholder='optional topic' />
    <button onClick={generate}>Generate cards</button>
    {loading && <div><p>Searching useful material with Tavily...</p><p>Extracting reusable English...</p><p>Preparing Chinese transfer prompts...</p></div>}
    <StackedLearningCards cards={cards} onSubmit={onSubmit} onAdvance={onAdvance} onFinish={onFinish} activeIndex={activeIndex} />
    {!!cards.length && !summary && <button onClick={onFinish}>Finish round</button>}
    <RoundSummary summary={summary} />
  </main>;
}
