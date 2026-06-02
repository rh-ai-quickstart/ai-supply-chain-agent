import ReactMarkdown from "react-markdown";
import { normalizeChatMarkdown } from "../utils/chatMarkdownNormalize";

export function ChatMarkdownBody({ content, compact, streaming = false }) {
  if (streaming) {
    const plainClass = ["chat-md-plain", compact ? "chat-md-plain--compact" : ""]
      .filter(Boolean)
      .join(" ");
    return (
      <div className={plainClass}>
        {content}
        <span className="chat-stream-cursor" aria-hidden="true">
          ▌
        </span>
      </div>
    );
  }

  const rootClass = ["chat-md", compact ? "chat-md--compact" : ""].filter(Boolean).join(" ");
  return (
    <div className={rootClass}>
      <ReactMarkdown>{normalizeChatMarkdown(content)}</ReactMarkdown>
    </div>
  );
}
