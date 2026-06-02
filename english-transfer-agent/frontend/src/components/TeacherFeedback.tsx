import type { AnswerEvaluation, Mistake } from '../api/agentClient';

type Props = {
  evaluation: AnswerEvaluation;
};

function firstMistake(mistakes?: Mistake[]) {
  return mistakes?.[0];
}

function Section({ className = '', label, children }: { className?: string; label: string; children?: React.ReactNode }) {
  if (!children) return null;
  return (
    <section className={`feedback-section ${className}`}>
      <div className="kicker">{label}</div>
      <p>{children}</p>
    </section>
  );
}

export default function TeacherFeedback({ evaluation }: Props) {
  const mistake = firstMistake(evaluation.mistakes);
  const didWell = evaluation.targetUsed
    ? `你已经把目标表达用进去了，迁移质量是 ${evaluation.targetUsageQuality}。`
    : undefined;

  return (
    <div className="feedback-grid" aria-label="Teacher feedback">
      <Section className="teacher" label="Teacher says">
        {evaluation.teacherResponseChinese || evaluation.adviceChinese}
      </Section>
      <Section className="good" label="What you did well">
        {didWell}
      </Section>
      <Section className="issue" label="Main issue">
        {mistake ? `${mistake.original} → ${mistake.correction}。${mistake.explanationChinese}` : undefined}
      </Section>
      <Section className="corrected" label="Corrected answer">
        <span className="answer-line">{evaluation.correctedAnswer}</span>
      </Section>
      <Section className="natural" label="Natural version">
        <span className="answer-line">{evaluation.naturalVersion}</span>
      </Section>
      <Section className="advanced" label="Advanced version">
        <span className="answer-line">{evaluation.advancedVersion}</span>
      </Section>
      <Section className="lesson" label="Mini lesson">
        {evaluation.microLessonChinese || evaluation.mainTeachingPoint}
      </Section>
      <Section className="lesson" label="Sentence frame">
        {evaluation.sentenceFrame}
      </Section>
    </div>
  );
}
