import type { AnswerEvaluation, Mistake } from '../api/agentClient';

type Props = {
  evaluation: AnswerEvaluation;
  target: string;
};

function firstMistake(mistakes?: Mistake[]) {
  return mistakes?.[0];
}

function normalize(value?: string | null) {
  return value?.trim().replace(/\s+/g, ' ');
}

function areSameAnswer(left?: string, right?: string) {
  const normalizedLeft = normalize(left)?.toLowerCase();
  const normalizedRight = normalize(right)?.toLowerCase();
  return Boolean(normalizedLeft && normalizedRight && normalizedLeft === normalizedRight);
}

function conciseLesson(value?: string | null) {
  if (!value) return undefined;

  const parts = value
    .split(/(?<=[。！？!?])\s*|\n+/)
    .map((part) => part.trim())
    .filter(Boolean);

  return parts.slice(0, 3).join(' ');
}

function mainFix(evaluation: AnswerEvaluation, target: string, mistake?: Mistake) {
  if (!evaluation.targetUsed) return `Missing target phrase: “${target}”`;
  if (mistake) return `${mistake.type === 'grammar' ? 'Grammar' : 'Main issue'}: “${mistake.original}” → “${mistake.correction}”`;
  return `Keep using: “${target}”`;
}

function teacherParagraph(evaluation: AnswerEvaluation, target: string, mistake?: Mistake) {
  const didWell = evaluation.targetUsed
    ? `你已经尝试使用“${target}”，这点很好。`
    : '你的回答已经回应了题目意思，这点很好。';
  const problem = !evaluation.targetUsed
    ? `主要问题是还没有用到目标表达“${target}”。`
    : mistake
      ? `主要问题是“${mistake.original}”这里需要改成“${mistake.correction}”。`
      : '现在主要是让句子更自然、更稳定。';

  return `${didWell}${problem}`;
}

function BetterAnswer({ evaluation }: { evaluation: AnswerEvaluation }) {
  const corrected = evaluation.correctedAnswer;
  const natural = evaluation.naturalVersion;
  const sameAnswer = areSameAnswer(corrected, natural);

  if (!corrected && !natural) return null;

  return (
    <section className="teacher-row better-answer">
      <div className="kicker">Better answer</div>
      {corrected && <p className="answer-line">{corrected}</p>}
      {natural && !sameAnswer && (
        <p className="answer-line answer-line-secondary">More natural: {natural}</p>
      )}
    </section>
  );
}

function AdvancedDetails({ evaluation }: { evaluation: AnswerEvaluation }) {
  if (!evaluation.advancedVersion) return null;

  return (
    <details className="reveal compact-reveal">
      <summary>Advanced version</summary>
      <div className="history-item">
        <p className="answer-line">{evaluation.advancedVersion}</p>
      </div>
    </details>
  );
}

function MistakeList({ mistakes }: { mistakes?: Mistake[] }) {
  if (!mistakes?.length) return null;

  return (
    <details className="reveal compact-reveal">
      <summary>Full mistake list</summary>
      {mistakes.map((mistake, index) => (
        <div className="history-item" key={`${mistake.original}-${index}`}>
          <div className="kicker">{mistake.type}</div>
          <p className="answer-line">{mistake.original} → {mistake.correction}</p>
          <p className="muted">{mistake.explanationChinese}</p>
        </div>
      ))}
    </details>
  );
}

export default function TeacherFeedback({ evaluation, target }: Props) {
  const mistake = firstMistake(evaluation.mistakes);
  const lesson = conciseLesson(evaluation.microLessonChinese || evaluation.mainTeachingPoint);

  return (
    <div className="teacher-feedback" aria-label="Teacher feedback">
      <section className="teacher-panel">
        <div className="kicker">Teacher says</div>
        <p>{teacherParagraph(evaluation, target, mistake)}</p>

        <div className="teacher-row main-fix">
          <div className="kicker">Main fix</div>
          <p>{mainFix(evaluation, target, mistake)}</p>
          {mistake?.explanationChinese && <p className="muted">{mistake.explanationChinese}</p>}
        </div>

        <BetterAnswer evaluation={evaluation} />

        {lesson && (
          <section className="teacher-row mini-lesson">
            <div className="kicker">Mini lesson</div>
            <p>{lesson}</p>
          </section>
        )}
      </section>

      <div className="advanced-details">
        <AdvancedDetails evaluation={evaluation} />
        <MistakeList mistakes={evaluation.mistakes} />
      </div>
    </div>
  );
}
