import ReactMarkdown from "react-markdown";

function normalizeChatMarkdown(markdown) {
  let text = markdown.trim();
  text = text.replace(/([:;])\s+(\d{1,2}\.\s+(?=\S))/g, "$1\n\n$2");
  text = text.replace(/([.!?])\s+(\d{1,2}\.\s+(?=\S))/g, "$1\n\n$2");
  return text;
}

export function ChatMarkdownBody({ content, compact }) {
  const rootClass = ["chat-md", compact ? "chat-md--compact" : ""].filter(Boolean).join(" ");
  return (
    <div className={rootClass}>
      <ReactMarkdown>{normalizeChatMarkdown(content)}</ReactMarkdown>
    </div>
  );
}
