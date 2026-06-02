export default function RoundSummary({ summary }: { summary: any }) {
  if (!summary) return null;
  return <div style={{ marginTop: 18 }}><h3>Round Summary</h3><pre>{JSON.stringify(summary, null, 2)}</pre></div>;
}
