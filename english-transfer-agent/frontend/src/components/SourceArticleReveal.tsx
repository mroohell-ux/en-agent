import type { SourceArticle } from '../api/agentClient';

type Props = {
  articles: SourceArticle[];
};

export default function SourceArticleReveal({ articles }: Props) {
  if (!articles.length) return null;

  return (
    <details className="reveal source-article-reveal">
      <summary>Searched full article{articles.length > 1 ? `s (${articles.length})` : ''}</summary>
      {articles.map((article) => (
        <article className="history-item source-article" key={article.url}>
          <div className="source-article-header">
            <div>
              <div className="kicker">Source article</div>
              <h2>{article.title}</h2>
              <p className="muted">{article.site}</p>
            </div>
            {article.url && (
              <a className="source-link" href={article.url} target="_blank" rel="noreferrer">
                Open link
              </a>
            )}
          </div>
          <div className="article-body-text">{article.content}</div>
        </article>
      ))}
    </details>
  );
}
