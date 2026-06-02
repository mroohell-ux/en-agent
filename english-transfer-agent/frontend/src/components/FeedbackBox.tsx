export default function FeedbackBox({ feedback }: { feedback: any }) {
  if (!feedback) return null;
  return <div style={{ background: '#f4f4f4', padding: 12, borderRadius: 10, marginTop: 10 }}>
    <strong>Teacher says</strong>
    <p>{feedback.teacherResponseChinese || feedback.adviceChinese}</p>
    <div>Score: {feedback.score}</div>
    <div>Target transfer: {feedback.targetUsageQuality}</div>
    {feedback.mainTeachingPoint && <div>Main teaching point: {feedback.mainTeachingPoint}</div>}
    {feedback.microLessonChinese && <div>Micro lesson: {feedback.microLessonChinese}</div>}
    {feedback.sentenceFrame && <div>Sentence frame: {feedback.sentenceFrame}</div>}
    {feedback.retryPromptChinese && <div>Retry prompt: {feedback.retryPromptChinese}</div>}
    {feedback.followUpPromptChinese && <div>Follow-up prompt: {feedback.followUpPromptChinese}</div>}
    <div>Corrected: {feedback.correctedAnswer}</div>
    <div>Natural: {feedback.naturalVersion}</div>
    <div>Advanced: {feedback.advancedVersion}</div>
    <div>Memory: {feedback.memoryDecision?.action}</div>
    <div>Next: {feedback.nextAction}</div>
  </div>;
}
