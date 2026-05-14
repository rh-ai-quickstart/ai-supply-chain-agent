import ReactMarkdown from "react-markdown";
import { normalizeChatMarkdown } from "../utils/chatMarkdownNormalize";

export function ChatMarkdownBody({ content, compact }) {
  const rootClass = ["chat-md", compact ? "chat-md--compact" : ""].filter(Boolean).join(" ");
  return (
    <div className={rootClass}>
      <ReactMarkdown>{normalizeChatMarkdown(content)}</ReactMarkdown>
    </div>
  );
}
