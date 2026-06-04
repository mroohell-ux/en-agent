import { useEffect, useMemo, useState } from 'react';
import {
  ApiRequestError,
  createArticleLesson,
  finishLesson,
  listLessons,
  submitQuestionAnswer,
  submitRetell,
  submitUsefulLanguagePractice,
  type ArticleLesson,
  type LessonSummary,
  type TeacherCorrection,
  type TeacherQuestion,
  type UsefulLanguageItem,
} from './api/agentClient';
import './styles.css';

type Mode = 'overview' | 'retell' | 'questions' | 'language' | 'review';
type UserFacingError = { step: string; rootCause: string };

const SAMPLE_ARTICLE = `JD Vance's old comment about "childless cat ladies" unleashed fury after it resurfaced online. Critics took issue with the phrase because they saw it as sexist and dismissive of people who do not have children. The comment did not land well with many voters, especially women who felt it relied on old stereotypes. The debate also raised a bigger question: who is considered to have a direct stake in the country's future?`;

function describeError(err: unknown, fallbackStep: string): UserFacingError {
  if (err instanceof ApiRequestError) return { step: err.step || fallbackStep, rootCause: err.rootCause };
  if (err instanceof TypeError) return { step: 'Connect to backend', rootCause: 'The frontend could not reach the API server. Check that the backend is running.' };
  if (err instanceof Error) return { step: fallbackStep, rootCause: err.message };
  return { step: fallbackStep, rootCause: 'Something unexpected happened.' };
}

function typeLabel(type: string) {
  return type.replace(/_/g, ' ');
}

export default function App() {
  const [lessons, setLessons] = useState<ArticleLesson[]>([]);
  const [activeLesson, setActiveLesson] = useState<ArticleLesson | null>(null);
  const [mode, setMode] = useState<Mode>('overview');
  const [articleText, setArticleText] = useState(SAMPLE_ARTICLE);
  const [articleUrl, setArticleUrl] = useState('');
  const [level, setLevel] = useState('B2-C1');
  const [includeIelts, setIncludeIelts] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<UserFacingError | null>(null);
  const [transcript, setTranscript] = useState('');
  const [correction, setCorrection] = useState<TeacherCorrection | null>(null);
  const [summary, setSummary] = useState<LessonSummary | null>(null);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [languageIndex, setLanguageIndex] = useState(0);

  useEffect(() => {
    listLessons().then(setLessons).catch(() => undefined);
  }, []);

  const activeQuestion = useMemo<TeacherQuestion | null>(() => {
    if (!activeLesson?.questions.length) return null;
    return activeLesson.questions[Math.min(questionIndex, activeLesson.questions.length - 1)];
  }, [activeLesson, questionIndex]);

  const activeLanguage = useMemo<UsefulLanguageItem | null>(() => {
    if (!activeLesson?.usefulLanguage.length) return null;
    return activeLesson.usefulLanguage[Math.min(languageIndex, activeLesson.usefulLanguage.length - 1)];
  }, [activeLesson, languageIndex]);

  const refreshLessons = async (selectedId?: string) => {
    const fresh = await listLessons();
    setLessons(fresh);
    if (selectedId) {
      const selected = fresh.find((lesson) => lesson.id === selectedId);
      if (selected) setActiveLesson(selected);
    }
  };

  const createLesson = async () => {
    setLoading(true);
    setError(null);
    setCorrection(null);
    setSummary(null);
    try {
      const lesson = await createArticleLesson({ articleText, articleUrl, level, includeIelts });
      setActiveLesson(lesson);
      setMode('overview');
      await refreshLessons(lesson.id);
    } catch (err) {
      setError(describeError(err, 'Create article lesson'));
    } finally {
      setLoading(false);
    }
  };

  const submitCurrent = async () => {
    if (!activeLesson || !transcript.trim()) return;
    setLoading(true);
    setError(null);
    try {
      let result: TeacherCorrection;
      if (mode === 'retell') {
        result = await submitRetell(activeLesson.id, transcript);
      } else if (mode === 'questions' && activeQuestion) {
        result = await submitQuestionAnswer(activeLesson.id, activeQuestion.id, transcript);
      } else if (mode === 'language' && activeLanguage) {
        result = await submitUsefulLanguagePractice(activeLesson.id, activeLanguage.id, transcript);
      } else {
        return;
      }
      setCorrection(result);
      setTranscript('');
      await refreshLessons(activeLesson.id);
    } catch (err) {
      setError(describeError(err, 'Evaluate speaking answer'));
    } finally {
      setLoading(false);
    }
  };

  const finishActiveLesson = async () => {
    if (!activeLesson) return;
    setLoading(true);
    setError(null);
    try {
      setSummary(await finishLesson(activeLesson.id));
      setMode('review');
      await refreshLessons(activeLesson.id);
    } catch (err) {
      setError(describeError(err, 'Finish lesson'));
    } finally {
      setLoading(false);
    }
  };

  const openLesson = (lesson: ArticleLesson) => {
    setActiveLesson(lesson);
    setMode('overview');
    setCorrection(null);
    setSummary(null);
    setTranscript('');
  };

  return (
    <main className="app-shell article-app">
      <section className="hero article-hero" aria-label="Article speaking teacher">
        <div className="hero-copy">
          <p className="eyebrow">Read → Speak → Correct → Repeat → Reuse → Review</p>
          <h1>Article Speaking Coach</h1>
          <p>
            Turn one article into active English speaking practice. The article is source material; your output is the center.
          </p>
        </div>
        <div className="start-panel article-create-panel">
          <label className="topic-label" htmlFor="article-url">Article URL (optional)</label>
          <input id="article-url" className="topic-input" value={articleUrl} onChange={(event) => setArticleUrl(event.target.value)} placeholder="https://..." />
          <label className="topic-label" htmlFor="article-text">Paste article text</label>
          <textarea id="article-text" value={articleText} onChange={(event) => setArticleText(event.target.value)} />
          <div className="inline-controls">
            <select className="topic-input topic-select" value={level} onChange={(event) => setLevel(event.target.value)}>
              <option>B1-B2</option>
              <option>B2-C1</option>
              <option>C1-C2</option>
            </select>
            <label className="checkbox-label"><input type="checkbox" checked={includeIelts} onChange={(event) => setIncludeIelts(event.target.checked)} /> IELTS optional</label>
          </div>
          <button className="primary-button" onClick={createLesson} disabled={loading}>{loading ? 'Building lesson…' : 'Add article lesson'}</button>
        </div>
      </section>

      {error && <section className="error-card"><strong>{error.step}</strong><p>{error.rootCause}</p></section>}

      <section className="workspace-grid">
        <aside className="lesson-list panel-card">
          <div className="section-heading"><p className="eyebrow">My Articles</p><h2>Lesson List</h2></div>
          {lessons.length === 0 && <p className="muted">Create your first article lesson. Mock mode works without AI keys.</p>}
          {lessons.map((lesson) => (
            <button className={`lesson-row ${activeLesson?.id === lesson.id ? 'active' : ''}`} key={lesson.id} onClick={() => openLesson(lesson)}>
              <strong>{lesson.source.title}</strong>
              <span>{lesson.source.site || 'Article'} · {lesson.progress.answerCount} answers · {lesson.progress.mistakeCount} mistakes</span>
            </button>
          ))}
        </aside>

        <section className="lesson-workspace panel-card">
          {!activeLesson ? (
            <EmptyWorkspace />
          ) : (
            <>
              <LessonHeader lesson={activeLesson} />
              <ModeTabs mode={mode} setMode={(next) => { setMode(next); setCorrection(null); setTranscript(''); }} includeIelts={Boolean(activeLesson.ieltsTasks)} />
              {mode === 'overview' && <Overview lesson={activeLesson} go={setMode} />}
              {mode === 'retell' && (
                <SpeakingTask
                  title="Say the Main Idea"
                  badge={`${activeLesson.retellTask.targetSpeakingSeconds}s speaking target`}
                  prompt={activeLesson.retellTask.prompt}
                  hints={activeLesson.retellTask.hints}
                  transcript={transcript}
                  setTranscript={setTranscript}
                  submitLabel="Submit main idea"
                  loading={loading}
                  onSubmit={submitCurrent}
                />
              )}
              {mode === 'questions' && activeQuestion && (
                <SpeakingTask
                  title="Answer Questions"
                  badge={typeLabel(activeQuestion.type)}
                  prompt={activeQuestion.question}
                  hints={[...activeQuestion.expectedIdeas, activeQuestion.usefulExpressionHint ? `Try using: ${activeQuestion.usefulExpressionHint}` : '']}
                  transcript={transcript}
                  setTranscript={setTranscript}
                  submitLabel="Submit answer"
                  loading={loading}
                  onSubmit={submitCurrent}
                  footer={<Pager current={questionIndex + 1} total={activeLesson.questions.length} onPrev={() => setQuestionIndex(Math.max(0, questionIndex - 1))} onNext={() => setQuestionIndex(Math.min(activeLesson.questions.length - 1, questionIndex + 1))} />}
                />
              )}
              {mode === 'language' && activeLanguage && (
                <SpeakingTask
                  title="Learn Useful English"
                  badge={activeLanguage.category.replace(/_/g, ' ')}
                  prompt={activeLanguage.reusePrompt}
                  hints={[`Expression: ${activeLanguage.text}`, `Meaning: ${activeLanguage.meaning}`, `Example: ${activeLanguage.example}`]}
                  transcript={transcript}
                  setTranscript={setTranscript}
                  submitLabel="Use it in my sentence"
                  loading={loading}
                  onSubmit={submitCurrent}
                  footer={<Pager current={languageIndex + 1} total={activeLesson.usefulLanguage.length} onPrev={() => setLanguageIndex(Math.max(0, languageIndex - 1))} onNext={() => setLanguageIndex(Math.min(activeLesson.usefulLanguage.length - 1, languageIndex + 1))} />}
                />
              )}
              {correction && <TeacherFeedback correction={correction} onRepeat={() => window.alert(correction.repeatPrompt)} />}
              {mode === 'review' && <Review lesson={activeLesson} summary={summary} finishLesson={finishActiveLesson} loading={loading} />}
              {mode !== 'review' && <div className="finish-panel"><button className="secondary-button" onClick={finishActiveLesson} disabled={loading}>Finish & review mistakes</button></div>}
            </>
          )}
        </section>
      </section>
    </main>
  );
}

function EmptyWorkspace() {
  return <div className="empty-workspace"><p className="eyebrow">Speaking-first</p><h2>Add or continue an article lesson</h2><p>Practice one task at a time: say the main idea, answer article questions, reuse useful language, then review corrections.</p></div>;
}

function LessonHeader({ lesson }: { lesson: ArticleLesson }) {
  return <header className="lesson-header"><p className="eyebrow">{lesson.level} · {lesson.source.site || 'Article'}</p><h2>{lesson.source.title}</h2><p>{lesson.mainIdea}</p></header>;
}

function ModeTabs({ mode, setMode, includeIelts }: { mode: Mode; setMode: (mode: Mode) => void; includeIelts: boolean }) {
  return <nav className="mode-tabs" aria-label="Lesson modes">
    <button className={mode === 'overview' ? 'active' : ''} onClick={() => setMode('overview')}>Overview</button>
    <button className={mode === 'retell' ? 'active' : ''} onClick={() => setMode('retell')}>1. Say the Main Idea</button>
    <button className={mode === 'questions' ? 'active' : ''} onClick={() => setMode('questions')}>2. Answer Questions</button>
    <button className={mode === 'language' ? 'active' : ''} onClick={() => setMode('language')}>3. Learn Useful English</button>
    <button className={mode === 'review' ? 'active' : ''} onClick={() => setMode('review')}>Review</button>
    {includeIelts && <span className="ielts-pill">IELTS practice available</span>}
  </nav>;
}

function Overview({ lesson, go }: { lesson: ArticleLesson; go: (mode: Mode) => void }) {
  return <div className="overview-grid">
    <button className="mode-card" onClick={() => go('retell')}><span>Speak</span><strong>Say the Main Idea</strong><p>{lesson.retellTask.prompt}</p></button>
    <button className="mode-card" onClick={() => go('questions')}><span>Answer</span><strong>Article Questions</strong><p>{lesson.questions.length} comprehension, explanation, opinion, personal, and advanced questions.</p></button>
    <button className="mode-card" onClick={() => go('language')}><span>Reuse</span><strong>Useful English</strong><p>{lesson.usefulLanguage.length} reusable expressions, words, grammar, and sentence patterns.</p></button>
    {lesson.ieltsTasks && <div className="mode-card passive"><span>Optional</span><strong>IELTS Practice</strong><p>Listening, reading, writing, and speaking tasks are generated from the same article, but speaking remains the center.</p></div>}
    <div className="key-points"><h3>Key points to retell</h3><ul>{lesson.keyPoints.map((point) => <li key={point}>{point}</li>)}</ul></div>
  </div>;
}

function SpeakingTask(props: { title: string; badge: string; prompt: string; hints: string[]; transcript: string; setTranscript: (value: string) => void; submitLabel: string; loading: boolean; onSubmit: () => void; footer?: React.ReactNode }) {
  return <section className="speaking-task">
    <div className="task-topline"><p className="eyebrow">{props.title}</p><span className="badge type">{props.badge}</span></div>
    <h3>{props.prompt}</h3>
    <ul className="hint-list">{props.hints.filter(Boolean).map((hint) => <li key={hint}>{hint}</li>)}</ul>
    <div className="mic-panel"><div className="mic-button" aria-hidden="true">🎙️</div><div><strong>Speak first</strong><p>Use the text box as a live transcript or fallback input.</p></div></div>
    <textarea value={props.transcript} onChange={(event) => props.setTranscript(event.target.value)} placeholder="Speak or type your answer here…" />
    <button className="primary-button" disabled={props.loading || !props.transcript.trim()} onClick={props.onSubmit}>{props.loading ? 'Checking…' : props.submitLabel}</button>
    {props.footer}
  </section>;
}

function Pager({ current, total, onPrev, onNext }: { current: number; total: number; onPrev: () => void; onNext: () => void }) {
  return <div className="pager"><button className="secondary-button" onClick={onPrev} disabled={current <= 1}>Previous</button><span>{current} / {total}</span><button className="secondary-button" onClick={onNext} disabled={current >= total}>Next</button></div>;
}

function TeacherFeedback({ correction, onRepeat }: { correction: TeacherCorrection; onRepeat: () => void }) {
  return <section className="teacher-feedback article-feedback"><div className="feedback-score"><span>{correction.score}</span><p>Teacher score</p></div><div className="teacher-panel"><p className="eyebrow">Teacher Feedback</p><p>{correction.overallFeedback}</p><div className="feedback-columns"><div><h4>Your better natural version</h4><p>{correction.naturalVersion}</p></div><div><h4>Advanced version</h4><p>{correction.advancedVersion}</p></div></div><h4>Key corrections</h4><ul>{correction.keyImprovements.map((item) => <li key={item}>{item}</li>)}</ul><div className="mistake-tabs">{correction.mistakes.map((mistake) => <article key={`${mistake.original}-${mistake.correction}`}><strong>{mistake.type}</strong><p><del>{mistake.original}</del> → {mistake.correction}</p><small>{mistake.explanation || mistake.explanationChinese}</small></article>)}</div><button className="primary-button" onClick={onRepeat}>Repeat better version</button></div></section>;
}

function Review({ lesson, summary, finishLesson, loading }: { lesson: ArticleLesson; summary: LessonSummary | null; finishLesson: () => void; loading: boolean }) {
  return <section className="review-screen"><div className="section-heading"><p className="eyebrow">Review</p><h3>Mistakes and useful expressions</h3></div>{!summary && <button className="primary-button" onClick={finishLesson} disabled={loading}>{loading ? 'Summarizing…' : 'Generate lesson summary'}</button>}{summary && <><h4>What you did well</h4><ul>{summary.whatUserDidWell.map((item) => <li key={item}>{item}</li>)}</ul><h4>Repeated mistakes</h4><div className="mistake-tabs">{summary.repeatedMistakes.map((mistake) => <article key={mistake.reviewItem || mistake.original}><strong>{mistake.type}</strong><p>{mistake.original} → {mistake.correction}</p></article>)}</div><h4>Useful expressions learned</h4><ul>{summary.usefulExpressionsLearned.map((item) => <li key={item.id}><strong>{item.text}</strong> — {item.meaning}</li>)}</ul><h4>Suggested next practice</h4><ul>{summary.suggestedNextPractice.map((item) => <li key={item}>{item}</li>)}</ul></>}<h4>All useful language from this lesson</h4><ul>{lesson.usefulLanguage.map((item) => <li key={item.id}><strong>{item.text}</strong>: {item.reusePrompt}</li>)}</ul></section>;
}
