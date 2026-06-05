import type { AnswerEvaluation, Mistake } from '../api/agentClient';

type Props = {
  evaluation: AnswerEvaluation;
  target: string;
  userAnswer: string;
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

function conciseText(value?: string | null) {
  if (!value) return undefined;

  const parts = value
    .split(/(?<=[。！？!?])\s*|\n+/)
    .map((part) => part.trim())
    .filter(Boolean);

  return parts.slice(0, 2).join(' ');
}

function thingDoneWell(evaluation: AnswerEvaluation, target: string) {
  if (evaluation.targetUsed) return `你已经尝试迁移目标表达“${target}”，这点很好。`;
  return '你先把中文意思表达出来了，这点很好。';
}

function mainProblem(evaluation: AnswerEvaluation, target: string, mistake?: Mistake) {
  if (!evaluation.targetUsed) return `主要问题：还没有用到目标表达“${target}”。`;
  if (mistake) return `主要问题：“${mistake.original}”需要改成“${mistake.correction}”。`;
  return '主要问题：继续把这个表达用得更自然、更稳定。';
}

function mainFix(evaluation: AnswerEvaluation, target: string, mistake?: Mistake) {
  if (!evaluation.targetUsed) return `Missing target: “${target}”`;
  if (mistake) return `Fix this: “${mistake.original}” → “${mistake.correction}”`;
  return `Keep this target: “${target}”`;
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
      {corrected && natural && !sameAnswer && (
        <p className="answer-line answer-line-secondary">More natural: {natural}</p>
      )}
      {!corrected && natural && <p className="answer-line">{natural}</p>}
    </section>
  );
}

function MiniLessonDetails({ evaluation }: { evaluation: AnswerEvaluation }) {
  const lesson = conciseText(evaluation.microLessonChinese || evaluation.mainTeachingPoint);
  if (!lesson) return null;

  return (
    <details className="reveal compact-reveal mini-lesson">
      <summary>Mini lesson</summary>
      <div className="history-item">
        <p>{lesson}</p>
      </div>
    </details>
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
  if (!mistakes?.length || mistakes.length < 2) return null;

  return (
    <details className="reveal compact-reveal">
      <summary>More mistake details</summary>
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

export default function TeacherFeedback({ evaluation, target, userAnswer }: Props) {
  const mistake = firstMistake(evaluation.mistakes);
  const shortFeedback = conciseText(evaluation.teacherResponseChinese || evaluation.adviceChinese);

  return (
    <div className="teacher-feedback" aria-label="Teacher feedback">
      <section className="teacher-row your-answer">
        <div className="kicker">Your answer</div>
        <p className="answer-line">{userAnswer}</p>
      </section>

      <section className="teacher-panel">
        <div className="kicker">Teacher says</div>
        {shortFeedback && <p>{shortFeedback}</p>}
        <div className="teacher-diagnosis">
          <div>
            <div className="kicker">One thing you did well</div>
            <p>{thingDoneWell(evaluation, target)}</p>
          </div>
          <div>
            <div className="kicker">One main problem</div>
            <p>{mainProblem(evaluation, target, mistake)}</p>
          </div>
        </div>
      </section>

      <section className="teacher-row main-fix">
        <div className="kicker">Main fix</div>
        <p>{mainFix(evaluation, target, mistake)}</p>
        {mistake?.explanationChinese && <p className="muted">{mistake.explanationChinese}</p>}
      </section>

      <BetterAnswer evaluation={evaluation} />

      <div className="advanced-details">
        <MiniLessonDetails evaluation={evaluation} />
        <AdvancedDetails evaluation={evaluation} />
        <MistakeList mistakes={evaluation.mistakes} />
      </div>
    </div>
  );
}
