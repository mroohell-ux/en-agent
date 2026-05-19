export default function FeedbackBox({ feedback }: { feedback: any }) {
  if (!feedback) return null;
  return <div style={{ background: '#f4f4f4', padding: 12, borderRadius: 10, marginTop: 10 }}>
    <div>Score: {feedback.score}</div>
    <div>{feedback.adviceChinese}</div>
    <div>Target transfer: {feedback.targetUsageQuality}</div>
    <div>Corrected: {feedback.correctedAnswer}</div>
    <div>Natural: {feedback.naturalVersion}</div>
    <div>Advanced: {feedback.advancedVersion}</div>
    <div>Memory: {feedback.memoryDecision?.action}</div>
  </div>;
}
