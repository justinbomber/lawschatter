import React, { memo } from 'react';

/**
 * 段落組件 - 使用與 LibreChat 相同的樣式
 * mb-2 = margin-bottom: 8px
 * whitespace-pre-wrap = 保留空白但自動換行
 */
export const p = memo(({ children }) => {
  return <p className="markdown-paragraph">{children}</p>;
});

/**
 * 程式碼組件 - 區分 inline 和 block code
 */
export const code = memo(({ inline, className, children, ...props }) => {
  return inline ? (
    <code className={className} {...props}>
      {children}
    </code>
  ) : (
    <pre>
      <code className={className} {...props}>
        {children}
      </code>
    </pre>
  );
});

/**
 * 連結組件
 */
export const a = memo(({ href, children }) => {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
});

/**
 * 標題組件
 */
export const h1 = memo(({ children }) => {
  return <h1 className="markdown-h1">{children}</h1>;
});

export const h2 = memo(({ children }) => {
  return <h2 className="markdown-h2">{children}</h2>;
});

export const h3 = memo(({ children }) => {
  return <h3 className="markdown-h3">{children}</h3>;
});

export const h4 = memo(({ children }) => {
  return <h4 className="markdown-h4">{children}</h4>;
});

/**
 * 列表組件
 */
export const ul = memo(({ children }) => {
  return <ul className="markdown-ul">{children}</ul>;
});

export const ol = memo(({ children }) => {
  return <ol className="markdown-ol">{children}</ol>;
});

export const li = memo(({ children }) => {
  return <li className="markdown-li">{children}</li>;
});

/**
 * 引用組件
 */
export const blockquote = memo(({ children }) => {
  return <blockquote className="markdown-blockquote">{children}</blockquote>;
});

/**
 * 表格組件
 */
export const table = memo(({ children }) => {
  return <table className="markdown-table">{children}</table>;
});

export const thead = memo(({ children }) => {
  return <thead className="markdown-thead">{children}</thead>;
});

export const tbody = memo(({ children }) => {
  return <tbody className="markdown-tbody">{children}</tbody>;
});

export const tr = memo(({ children }) => {
  return <tr className="markdown-tr">{children}</tr>;
});

export const th = memo(({ children }) => {
  return <th className="markdown-th">{children}</th>;
});

export const td = memo(({ children }) => {
  return <td className="markdown-td">{children}</td>;
});

/**
 * 水平線組件
 */
export const hr = memo(() => {
  return <hr className="markdown-hr" />;
});

/**
 * 強調組件
 */
export const strong = memo(({ children }) => {
  return <strong className="markdown-strong">{children}</strong>;
});

export const em = memo(({ children }) => {
  return <em className="markdown-em">{children}</em>;
});

