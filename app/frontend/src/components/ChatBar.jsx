export function ChatBar({
  chatInput,
  onChangeChatInput,
  onSubmitChat,
  chatLoading,
  chatError,
  chatMessages,
}) {
  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmitChat();
    }
  };

  return (
    <section className="chat-section">
      <div className="chat-history">
        {chatMessages.length === 0 ? (
          <p className="muted">No chat messages yet.</p>
        ) : (
          chatMessages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`chat-msg ${message.role}`}>
              <strong>{message.role === "human" ? "You" : "AI"}:</strong> {message.content}
            </div>
          ))
        )}
      </div>
      {chatError && <p className="error">{chatError}</p>}
      <footer className="chat-bar">
        <input
          type="text"
          placeholder="Ask me anything..."
          value={chatInput}
          onChange={(event) => onChangeChatInput(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={chatLoading}
        />
        <button type="button" onClick={onSubmitChat} disabled={chatLoading || !chatInput.trim()}>
          {chatLoading ? "..." : "➤"}
        </button>
      </footer>
    </section>
  );
}
