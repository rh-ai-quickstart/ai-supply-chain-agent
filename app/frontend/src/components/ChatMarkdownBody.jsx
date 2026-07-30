import PropTypes from "prop-types";
import ReactMarkdown from "react-markdown";
import { normalizeChatMarkdown } from "../utils/chatMarkdownNormalize";

export function ChatMarkdownBody({ content = "", compact = false }) {
  const rootClass = ["chat-md", compact ? "chat-md--compact" : ""].filter(Boolean).join(" ");
  return (
    <div className={rootClass}>
      <ReactMarkdown>{normalizeChatMarkdown(content)}</ReactMarkdown>
    </div>
  );
}

ChatMarkdownBody.propTypes = {
  content: PropTypes.string,
  compact: PropTypes.bool,
};
