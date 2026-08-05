import PropTypes from "prop-types";
import { useEffect, useRef, useState } from "react";
import { formatCompletionSummary } from "../utils/chatCompletionMeta.js";
import { safeJsonStringify } from "../utils/safeJsonStringify.js";
import { ChatMarkdownBody } from "./ChatMarkdownBody.jsx";

function messageBubbleClassName(role, compact) {
  const compactClass = compact ? " chat-message--compact" : "";
  return `chat-message ${role}${compactClass}`;
}

export function ChatBar({
  chatInput = "",
  onChangeChatInput,
  onSubmitChat,
  chatLoading = false,
  chatError = "",
  chatMessages = [],
  chatRagHint = "",
}) {
  const [isChatModalOpen, setIsChatModalOpen] = useState(false);
  const logEndRef = useRef(null);
  const modalInputRef = useRef(null);
  const wasChatLoadingRef = useRef(false);
  const previouslyFocusedRef = useRef(null);

  useEffect(() => {
    if (!isChatModalOpen || !logEndRef.current) {
      return;
    }
    logEndRef.current.scrollIntoView?.({ behavior: "smooth", block: "end" });
     
  }, [chatMessages, chatLoading, isChatModalOpen]);

  // When a slow reply finishes, surface the modal once (user can dismiss it afterward).
  useEffect(() => {
    if (wasChatLoadingRef.current && !chatLoading) {
      const last = chatMessages[chatMessages.length - 1];
      if (last?.role === "ai") {
         
        setIsChatModalOpen(true);
      }
    }
    wasChatLoadingRef.current = chatLoading;
  }, [chatMessages, chatLoading]);

  useEffect(() => {
    if (!isChatModalOpen) {
      return;
    }
    previouslyFocusedRef.current = document.activeElement;
    const timer = window.setTimeout(() => modalInputRef.current?.focus(), 0);

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setIsChatModalOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", onKeyDown);
      const prior = previouslyFocusedRef.current;
      if (prior && typeof prior.focus === "function") {
        prior.focus();
      }
    };
  }, [isChatModalOpen]);

  const openModal = () => setIsChatModalOpen(true);
  const closeModal = () => setIsChatModalOpen(false);

  const handleSend = () => {
    const trimmed = chatInput.trim();
    if (!trimmed || chatLoading) {
      return;
    }
    if (!isChatModalOpen) {
      openModal();
    }
    void onSubmitChat();
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const renderMessageLog = (compact) => (
    <>
      {chatMessages.length === 0 ? (
        <p className="muted">No chat messages yet.</p>
      ) : (
        chatMessages.map((message, index) => {
          const hasCompletion =
            message.role === "ai" &&
            message.completion &&
            Object.keys(message.completion).length > 0;
          const completionSummary = hasCompletion ? formatCompletionSummary(message.completion) : "";
          return (
            <div key={`${message.role}-${index}`} className={messageBubbleClassName(message.role, compact)}>
              {message.role === "ai" ? (
                <>
                  {["general_simulation", "fetch_news", "knowledge_base"].includes(message.tool) ? (
                    <p className="muted chat-tool-badge">Used tool: {message.tool}</p>
                  ) : null}
                  <ChatMarkdownBody content={message.content} compact={compact} />
                  {hasCompletion && message.completion ? (
                    <div className="chat-completion-meta">
                      {completionSummary ? <p className="chat-completion-summary">{completionSummary}</p> : null}
                      {!compact ? (
                        <details className="chat-completion-details">
                          <summary>Response details</summary>
                          <pre>{safeJsonStringify(message.completion)}</pre>
                        </details>
                      ) : null}
                    </div>
                  ) : null}
                </>
              ) : (
                message.content
              )}
            </div>
          );
        })
      )}
      {chatLoading ? <p className="muted">Thinking…</p> : null}
      {chatError ? <p className="error">{chatError}</p> : null}
      {chatRagHint ? (
        <p className="muted" role="status">
          {chatRagHint}
        </p>
      ) : null}
      {compact ? null : <div ref={logEndRef} />}
    </>
  );

  return (
    <>
      <div className="chat-bar-container">
        {!isChatModalOpen && chatMessages.length > 0 ? (
          <div className="chat-bar-preview" data-test="chat-collapsed-preview">
            {renderMessageLog(true)}
          </div>
        ) : null}
        <div className="chat-bar-row">
          <input
            type="text"
            placeholder="Ask me anything..."
            value={chatInput}
            onChange={(event) => onChangeChatInput(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={chatLoading}
            aria-label="Chat input"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={chatLoading || !chatInput.trim()}
            aria-label={chatLoading ? "Sending" : "Send chat message"}
          >
            {chatLoading ? "…" : "➤"}
          </button>
          {chatMessages.length > 0 ? (
            <button type="button" className="chat-history-btn" onClick={openModal}>
              View conversation
            </button>
          ) : null}
        </div>
      </div>

      {isChatModalOpen ? (
        <div
          className="chat-modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="chat-modal-title"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              closeModal();
            }
          }}
        >
          <div className="chat-modal-content">
            <div className="chat-modal-header">
              <h3 id="chat-modal-title">AI Assistant</h3>
              <button type="button" className="chat-modal-dismiss" onClick={closeModal} aria-label="Close dialog">
                ×
              </button>
            </div>
            <div className="chat-log-display">{renderMessageLog(false)}</div>
            <div className="chat-modal-composer">
              <input
                ref={modalInputRef}
                type="text"
                placeholder="Ask me anything..."
                value={chatInput}
                onChange={(event) => onChangeChatInput(event.target.value)}
                onKeyDown={handleKeyDown}
                disabled={chatLoading}
                aria-label="Chat reply input"
              />
              <button type="button" onClick={handleSend} disabled={chatLoading || !chatInput.trim()}>
                Send
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

ChatBar.propTypes = {
  chatInput: PropTypes.string,
  onChangeChatInput: PropTypes.func,
  onSubmitChat: PropTypes.func,
  chatLoading: PropTypes.bool,
  chatError: PropTypes.string,
  chatMessages: PropTypes.array,
  chatRagHint: PropTypes.string,
};
