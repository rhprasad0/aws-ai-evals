import { FormEvent, useMemo, useState } from 'react';
import { askChatbot, ChatResponse } from '../api/chat';

const PROMPTS = [
  'Where does Ryan show container orchestration?',
  'Where does Ryan show AWS-native orchestration?',
  'Where does Ryan show RAG or semantic search?',
  'Where does Ryan show eval engineering?',
  'What evidence supports Ryan as an AI systems builder?',
  'Which claims are lab/project evidence rather than production evidence?',
];

const MAX_MESSAGE_CHARS = 2000;

type Status = 'idle' | 'loading' | 'error';

function getSessionId(): string {
  const key = 'ryanprasad-chatbot-session-id';
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;
  const next = crypto.randomUUID();
  window.localStorage.setItem(key, next);
  return next;
}

export default function ChatPanel() {
  const sessionId = useMemo(getSessionId, []);
  const [question, setQuestion] = useState(PROMPTS[0]);
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState('');
  const [answer, setAnswer] = useState<ChatResponse | null>(null);

  async function submit(nextQuestion = question) {
    if (!nextQuestion.trim()) return;
    if (nextQuestion.length > MAX_MESSAGE_CHARS) {
      setError('Keep questions under 2,000 characters. The backend also enforces this.');
      setStatus('error');
      return;
    }

    setStatus('loading');
    setError('');
    setAnswer(null);
    try {
      const result = await askChatbot(sessionId, nextQuestion.trim());
      if ('error' in result) {
        setStatus('error');
        setError(errorMessage(result.error));
        return;
      }
      setAnswer(result);
      setStatus('idle');
    } catch {
      setStatus('error');
      setError('The evidence bot is unavailable. Try again in a minute.');
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit();
  }

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">ryanprasad.ai / candidate evidence bot</p>
        <h1>Ask what Ryan can actually prove.</h1>
        <p className="lede">
          This V1 answers from a curated public profile and reviewed source labels. It is built to cite evidence,
          calibrate strength, and say “not supported” instead of résumé fan fiction.
        </p>
      </section>

      <section className="panel" aria-label="Evidence chatbot">
        <div className="chips" aria-label="Suggested questions">
          {PROMPTS.map((prompt) => (
            <button
              className="chip"
              key={prompt}
              type="button"
              onClick={() => {
                setQuestion(prompt);
                void submit(prompt);
              }}
            >
              {prompt}
            </button>
          ))}
        </div>

        <form onSubmit={onSubmit} className="ask-form">
          <label htmlFor="question">Recruiter question</label>
          <textarea
            id="question"
            value={question}
            maxLength={MAX_MESSAGE_CHARS}
            onChange={(event) => setQuestion(event.target.value)}
          />
          <div className="form-row">
            <span>{question.length}/{MAX_MESSAGE_CHARS}</span>
            <button disabled={status === 'loading'} type="submit">
              {status === 'loading' ? 'Checking evidence…' : 'Ask'}
            </button>
          </div>
        </form>

        {status === 'error' && <p className="error" role="alert">{error}</p>}

        {answer && (
          <article className="answer">
            <h2>Answer</h2>
            <p>{answer.answer}</p>
            <dl>
              <div>
                <dt>Evidence strength</dt>
                <dd>{answer.evidenceStrength}</dd>
              </div>
              <div>
                <dt>Citations</dt>
                <dd>{answer.citations.length ? answer.citations.join('; ') : 'No supporting public source labels'}</dd>
              </div>
            </dl>
            {answer.unsupportedClaims.length > 0 && (
              <div className="warning">
                Unsupported claims: {answer.unsupportedClaims.join('; ')}
              </div>
            )}
          </article>
        )}
      </section>
    </main>
  );
}

function errorMessage(error: string): string {
  if (error === 'validation_error') return 'That request did not fit the chatbot contract.';
  if (error === 'rate_limited') return 'Too many requests. Let the résumé raccoon cool down for a minute.';
  return 'The evidence bot is unavailable. Try again in a minute.';
}
