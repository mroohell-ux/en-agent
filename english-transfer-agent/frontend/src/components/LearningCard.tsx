import { useState } from 'react';
import FeedbackBox from './FeedbackBox';

export default function LearningCard({ card, onSubmit, onAdvance, onFinish, active, index, total }: any) {
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState<any>(null);
  const [currentPrompt, setCurrentPrompt] = useState(card.chinesePrompt);
  const [showRef, setShowRef] = useState(false);

  const submit = async () => {
    const nextFeedback = await onSubmit(card.id, answer);
    setFeedback(nextFeedback);
    if (nextFeedback.nextAction === 'follow_up_question' && nextFeedback.followUpPromptChinese) {
      setCurrentPrompt(nextFeedback.followUpPromptChinese);
      setAnswer('');
    }
    if ((nextFeedback.nextAction === 'give_hint' || nextFeedback.nextAction === 'micro_lesson' || nextFeedback.nextAction === 'try_again') && nextFeedback.retryPromptChinese) {
      setCurrentPrompt(nextFeedback.retryPromptChinese);
      setAnswer('');
    }
  };

  if (!active) return <div style={{ marginTop: 8, padding: 12, border: '1px solid #ddd', borderRadius: 12, opacity: 0.7 }}>{index + 1}. {card.title}</div>;
  return <div style={{ marginTop: 8, padding: 12, border: '1px solid #bbb', borderRadius: 12 }}>
    <div>Card {index + 1} / {total}</div>
    <h3>{card.type}</h3>
    <p>{currentPrompt}</p>
    <textarea value={answer} onChange={(e)=>setAnswer(e.target.value)} style={{ width: '100%', minHeight: 90 }} />
    <button onClick={submit}>Submit</button>
    <FeedbackBox feedback={feedback} />
    {feedback?.nextAction === 'next_card' && <button onClick={onAdvance}>Next Card</button>}
    {feedback?.nextAction === 'finish_round' && <button onClick={onFinish}>Finish Round</button>}
    <details open={showRef} onToggle={(e)=>setShowRef((e.target as HTMLDetailsElement).open)}>
      <summary>Show reference and target</summary>
      <p>Original: {card.originalReference}</p><p>Extracted: {card.extractedFromOriginal}</p><p>Target: {card.target}</p><p>Rewrite: {card.referenceExample}</p>
    </details>
  </div>;
}
