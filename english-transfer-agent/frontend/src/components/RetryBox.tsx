import type { AnswerEvaluation, NextAction } from '../api/agentClient';

type Props = {
  evaluation: AnswerEvaluation;
};

const RETRY_ACTIONS: NextAction[] = ['give_hint', 'micro_lesson', 'try_again', 'follow_up_question'];

function titleFor(nextAction: NextAction) {
  if (nextAction === 'give_hint') return 'Hint before your next attempt';
  if (nextAction === 'micro_lesson') return 'Mini lesson, then try again';
  if (nextAction === 'follow_up_question') return 'Follow-up question';
  return 'Try the same target again';
}

export default function RetryBox({ evaluation }: Props) {
  if (!RETRY_ACTIONS.includes(evaluation.nextAction)) return null;

  const prompt = evaluation.followUpPromptChinese || evaluation.retryPromptChinese || evaluation.teacherResponseChinese;

  return (
    <section className="retry-box" aria-label="Retry instructions">
      <h3 className="retry-title">{titleFor(evaluation.nextAction)}</h3>
      {prompt && <p>{prompt}</p>}
      {evaluation.sentenceFrame && <div className="frame">Sentence frame: {evaluation.sentenceFrame}</div>}
    </section>
  );
}
