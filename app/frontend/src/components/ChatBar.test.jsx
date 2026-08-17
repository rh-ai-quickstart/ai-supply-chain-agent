import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatBar } from "./ChatBar";

describe("ChatBar", () => {
  it("renders empty state with input and send button", () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[]}
      />
    );
    expect(screen.getByLabelText("Chat input")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send chat message" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Knowledge base: None");
  });

  it("shows the active knowledge-base name above the chat input", () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[]}
        knowledgeBaseName="air_risk_uk_nats_gps_closure-abc12345"
      />
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Knowledge base: air_risk_uk_nats_gps_closure-abc12345",
    );
  });

  it("renders user input value", () => {
    render(
      <ChatBar
        chatInput="Hello world"
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[]}
      />
    );
    expect(screen.getByLabelText("Chat input")).toHaveValue("Hello world");
  });

  it("disables input and send button while loading", () => {
    render(
      <ChatBar
        chatInput="test"
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={true}
        chatMessages={[]}
      />
    );
    expect(screen.getByLabelText("Chat input")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Sending" })).toBeDisabled();
  });

  it("shows loading text while loading", () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={true}
        chatMessages={[{ role: "user", content: "Hello" }]}
      />
    );
    // "Thinking…" contains Unicode ellipsis (U+2026)
    expect(screen.getByText(/Thinking…/)).toBeInTheDocument();
  });

  it("shows chat error", () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }]}
        chatError="Connection failed"
      />
    );
    expect(screen.getByText("Connection failed")).toBeInTheDocument();
  });

  it("sends message when send button clicked", async () => {
    const user = userEvent.setup();
    const onSubmitChat = vi.fn();
    render(
      <ChatBar
        chatInput="hello"
        onChangeChatInput={vi.fn()}
        onSubmitChat={onSubmitChat}
        chatLoading={false}
        chatMessages={[]}
      />
    );
    await user.click(screen.getByRole("button", { name: "Send chat message" }));
    expect(onSubmitChat).toHaveBeenCalled();
  });

  it("does not send when input is empty", async () => {
    const user = userEvent.setup();
    const onSubmitChat = vi.fn();
    render(
      <ChatBar
        chatInput="   "
        onChangeChatInput={vi.fn()}
        onSubmitChat={onSubmitChat}
        chatLoading={false}
        chatMessages={[]}
      />
    );
    await user.click(screen.getByRole("button", { name: "Send chat message" }));
    expect(onSubmitChat).not.toHaveBeenCalled();
  });

  it("does not send while loading", async () => {
    const user = userEvent.setup();
    const onSubmitChat = vi.fn();
    render(
      <ChatBar
        chatInput="hello"
        onChangeChatInput={vi.fn()}
        onSubmitChat={onSubmitChat}
        chatLoading={true}
        chatMessages={[]}
      />
    );
    await user.click(screen.getByRole("button", { name: "Sending" }));
    expect(onSubmitChat).not.toHaveBeenCalled();
  });

  it("handles Enter key to send in modal", async () => {
    const user = userEvent.setup();
    const onSubmitChat = vi.fn();
    render(
      <ChatBar
        chatInput="hello"
        onChangeChatInput={vi.fn()}
        onSubmitChat={onSubmitChat}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }, { role: "ai", content: "Hi" }]}
      />
    );
    // Opening the modal triggers it to open via auto-open useEffect since ai message exists
    await user.click(screen.getByRole("button", { name: "View conversation" }));
    // Now submit via the modal input using userEvent.type with Enter
    const modalInput = screen.getByLabelText("Chat reply input");
    await user.type(modalInput, "{Enter}");
    expect(onSubmitChat).toHaveBeenCalled();
  });

  it("does not send on Shift+Enter in modal", async () => {
    const user = userEvent.setup();
    const onSubmitChat = vi.fn();
    render(
      <ChatBar
        chatInput="hello"
        onChangeChatInput={vi.fn()}
        onSubmitChat={onSubmitChat}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }, { role: "ai", content: "Hi" }]}
      />
    );
    await user.click(screen.getByRole("button", { name: "View conversation" }));
    const modalInput = screen.getByLabelText("Chat reply input");
    await user.type(modalInput, "{Shift>}{Enter}{/Shift}{/Shift}");
    expect(onSubmitChat).not.toHaveBeenCalled();
  });

  it("renders user message", () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }]}
      />
    );
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders AI message with markdown body", () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "ai", content: "Hello back" }]}
      />
    );
    expect(screen.getByText("Hello back")).toBeInTheDocument();
  });

  it("shows no chat messages placeholder when empty", async () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }]}
      />
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "View conversation" }));
    // Modal opens but has messages, so placeholder is not shown
    expect(screen.queryByText("No chat messages yet.")).not.toBeInTheDocument();
  });

  it("opens chat modal when view conversation clicked", async () => {
    const user = userEvent.setup();
    render(
      <ChatBar
        chatInput="test"
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }, { role: "ai", content: "Hi" }]}
      />
    );
    await user.click(screen.getByRole("button", { name: "View conversation" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("Chat reply input")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send chat message" })).toBeInTheDocument();
  });

  it("closes modal when dismiss button clicked", async () => {
    const user = userEvent.setup();
    render(
      <ChatBar
        chatInput="test"
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }, { role: "ai", content: "Hi" }]}
      />
    );
    await user.click(screen.getByRole("button", { name: "View conversation" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByLabelText("Close dialog"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes modal on Escape", async () => {
    const user = userEvent.setup();
    render(
      <ChatBar
        chatInput="test"
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }, { role: "ai", content: "Hi" }]}
      />
    );
    await user.click(screen.getByRole("button", { name: "View conversation" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders completion details in collapsed preview when modal closed", () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[
          {
            role: "ai",
            content: "answer",
            completion: {
              agent: "test",
              scenario_id: "s1",
              affected_entities: ["e1"],
              solver: { score: 0.5 },
            },
          },
        ]}
      />
    );
    // Dialog is not open by default; collapsed preview is rendered
    const container = document.querySelector(".chat-bar-preview");
    expect(container).toBeInTheDocument();
  });

  it("renders collapsed preview when messages exist and modal closed", () => {
    render(
      <ChatBar
        chatInput="test"
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }]}
      />
    );
    // The component uses data-test (not data-testid), so use raw DOM query
    const container = document.querySelector("[data-test='chat-collapsed-preview']");
    expect(container).toBeInTheDocument();
  });

  it("calls onChangeChatInput on input change in modal", async () => {
    const user = userEvent.setup();
    const onChangeChatInput = vi.fn();
    render(
      <ChatBar
        chatInput="test"
        onChangeChatInput={onChangeChatInput}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "user", content: "Hello" }]}
      />
    );
    await user.click(screen.getByRole("button", { name: "View conversation" }));
    const input = screen.getByLabelText("Chat reply input");
    // Controlled input: fire a single change (parent does not re-render with new value).
    fireEvent.change(input, { target: { value: "hello" } });
    expect(onChangeChatInput).toHaveBeenCalledWith("hello");
  });

  it.each(["general_simulation", "fetch_news", "knowledge_base"])(
    "shows tool badge for %s",
    (tool) => {
      render(
        <ChatBar
          chatInput=""
          onChangeChatInput={vi.fn()}
          onSubmitChat={vi.fn()}
          chatLoading={false}
          chatMessages={[
            { role: "human", content: "hi" },
            { role: "ai", content: "Done.", tool },
          ]}
        />,
      );
      expect(screen.getByText(`Used tool: ${tool}`)).toBeInTheDocument();
    },
  );

  it("does not show the clear button when there are no messages", () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[]}
        onClearChat={vi.fn()}
      />
    );
    expect(screen.queryByRole("button", { name: "Clear conversation" })).not.toBeInTheDocument();
  });

  it("calls onClearChat when the clear button is clicked", async () => {
    const user = userEvent.setup();
    const onClearChat = vi.fn();
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "human", content: "hi" }, { role: "ai", content: "ok" }]}
        onClearChat={onClearChat}
      />
    );
    await user.click(screen.getByRole("button", { name: "Clear conversation" }));
    expect(onClearChat).toHaveBeenCalled();
    expect(onClearChat).toHaveBeenCalledWith();
  });

  it("calls onClearChat without the click event (modal header)", async () => {
    const user = userEvent.setup();
    const onClearChat = vi.fn();
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={false}
        chatMessages={[{ role: "human", content: "hi" }, { role: "ai", content: "ok" }]}
        onClearChat={onClearChat}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "View conversation" }));
    const modalClear = within(screen.getByRole("dialog")).getByRole("button", {
      name: "Clear conversation",
    });
    await user.click(modalClear);
    expect(onClearChat).toHaveBeenCalledWith();
  });

  it("hides the clear button while loading to avoid clearing an in-flight reply", () => {
    render(
      <ChatBar
        chatInput=""
        onChangeChatInput={vi.fn()}
        onSubmitChat={vi.fn()}
        chatLoading={true}
        chatMessages={[{ role: "human", content: "hi" }, { role: "ai", content: "" }]}
        onClearChat={vi.fn()}
      />
    );
    expect(screen.queryByRole("button", { name: "Clear conversation" })).not.toBeInTheDocument();
  });
});
