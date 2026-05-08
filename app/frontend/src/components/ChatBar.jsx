import { useEffect, useRef, useState } from "react";
import { formatCompletionSummary } from "../utils/chatCompletionMeta.js";
import { ChatMarkdownBody } from "./ChatMarkdownBody.jsx";

function messageBubbleClassName(role, compact) {
  const compactClass = compact ? " chat-message--compact" : "";
  return `chat-message ${role}${compactClass}`;
}

export function ChatBar({
  chatInput,
  onChangeChatInput,
  onSubmitChat,
  chatLoading,
  chatError,
  chatMessages,
  vectorStores = [],
  vectorStoresLoading = false,
  vectorStoresError = "",
  selectedVectorStoreId = "",
  onChangeVectorStore,
}) {
  const [isChatModalOpen, setIsChatModalOpen] = useState(false);
  const logEndRef = useRef(null);
  const modalInputRef = useRef(null);

  useEffect(() => {
    if (isChatModalOpen && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [chatMessages, chatLoading, isChatModalOpen]);

  useEffect(() => {
    if (isChatModalOpen) {
      window.setTimeout(() => modalInputRef.current?.focus(), 0);
    }
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

  const renderVectorStoreRow = () => (
    <div className="chat-vector-row">
      <label className="chat-vector-label" htmlFor="chat-vector-store">
        Knowledge base
      </label>
      <select
        id="chat-vector-store"
        className="chat-vector-select"
        value={selectedVectorStoreId}
        onChange={(event) => onChangeVectorStore(event.target.value)}
        disabled={chatLoading || vectorStoresLoading}
        aria-label="Knowledge base"
        data-test="chat-vector-store"
      >
        <option value="">Default (dashboard PGVector)</option>
        {vectorStores.map((store) => (
          <option key={store.id} value={store.id}>
            {store.status && store.status !== "completed"
              ? `${store.name} (${store.status})`
              : store.name}
          </option>
        ))}
      </select>
      {vectorStoresError ? (
        <span className="chat-vector-error" role="status">
          {vectorStoresError}
        </span>
      ) : null}
    </div>
  );

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
                  <ChatMarkdownBody content={message.content} compact={compact} />
                  {hasCompletion && message.completion ? (
                    <div className="chat-completion-meta">
                      {completionSummary ? <p className="chat-completion-summary">{completionSummary}</p> : null}
                      {!compact ? (
                        <details className="chat-completion-details">
                          <summary>Response details</summary>
                          <pre>{JSON.stringify(message.completion, null, 2)}</pre>
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
      {compact ? null : <div ref={logEndRef} />}
    </>
  );

  return (
    <>
      <div className="chat-bar-container">
        {renderVectorStoreRow()}
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
          <button type="button" onClick={handleSend} disabled={chatLoading || !chatInput.trim()}>
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
