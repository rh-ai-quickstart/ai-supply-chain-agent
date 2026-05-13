import ReactMarkdown from 'react-markdown';

/**
 * Insert blank lines before inline ordered-list markers so CommonMark emits
 * proper lists (models often emit "include: 1. **Title**" on one line).
 */
function normalizeChatMarkdown(markdown: string): string {
  let text = markdown.trim();
  text = text.replace(/([:;])\s+(\d{1,2}\.\s+(?=\S))/g, '$1\n\n$2');
  text = text.replace(/([.!?])\s+(\d{1,2}\.\s+(?=\S))/g, '$1\n\n$2');
  return text;
}

export interface ChatMarkdownBodyProps {
  content: string;
  compact?: boolean;
}

export function ChatMarkdownBody({ content, compact }: ChatMarkdownBodyProps) {
  const rootClass = [
    'supply-chain-perspective__dashboard-chat-md',
    compact ? 'supply-chain-perspective__dashboard-chat-md--compact' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={rootClass}>
      <ReactMarkdown>{normalizeChatMarkdown(content)}</ReactMarkdown>
    </div>
  );
}
