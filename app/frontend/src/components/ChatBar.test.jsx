import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatBar } from "./ChatBar";

vi.mock("./ChatMarkdownBody.jsx", () => ({
  ChatMarkdownBody: ({ content, streaming }) => (
    <div data-testid="chat-md" data-streaming={streaming ? "true" : "false"}>
      {content}
    </div>
  ),
}));

function defaultProps(overrides = {}) {
  return {
    chatInput: "",
    onChangeChatInput: vi.fn(),
    onSubmitChat: vi.fn(),
    chatLoading: false,
    chatError: "",
    chatMessages: [],
    vectorStores: [],
    vectorStoresLoading: false,
    vectorStoresError: "",
    selectedVectorStoreId: "",
    onChangeVectorStore: vi.fn(),
    ...overrides,
  };
}

describe("ChatBar", () => {
  it("shows empty state in the modal after send opens it", async () => {
    const user = userEvent.setup();
    render(<ChatBar {...defaultProps({ chatInput: "hello" })} />);

    await user.click(screen.getByRole("button", { name: "➤" }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("No chat messages yet.")).toBeInTheDocument();
  });

  it("shows Thinking… in the preview while loading without a streaming assistant bubble", () => {
    render(
      <ChatBar
        {...defaultProps({
          chatLoading: true,
          chatMessages: [{ role: "human", content: "What is the delay?" }],
        })}
      />,
    );
    expect(document.querySelector('[data-test="chat-collapsed-preview"]')).toBeTruthy();
    expect(screen.getByText("Thinking…")).toBeInTheDocument();
  });

  it("hides Thinking… when the last assistant message is streaming", () => {
    render(
      <ChatBar
        {...defaultProps({
          chatLoading: true,
          chatMessages: [{ role: "ai", content: "partial", streaming: true }],
        })}
      />,
    );
    expect(screen.queryByText("Thinking…")).not.toBeInTheDocument();
    expect(screen.getByTestId("chat-md")).toHaveAttribute("data-streaming", "true");
  });

  it("displays chat errors in the message log", () => {
    render(
      <ChatBar
        {...defaultProps({
          chatError: "Failed to send chat request.",
          chatMessages: [{ role: "human", content: "Hello" }],
        })}
      />,
    );
    expect(screen.getByText("Failed to send chat request.")).toBeInTheDocument();
  });

  it("calls onSubmitChat when send is clicked with input", async () => {
    const props = defaultProps({ chatInput: "inventory levels?" });
    const user = userEvent.setup();
    render(<ChatBar {...props} />);

    await user.click(screen.getByRole("button", { name: "➤" }));

    expect(props.onSubmitChat).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("does not call onSubmitChat when input is empty or loading", async () => {
    const props = defaultProps({ chatLoading: true, chatInput: "hello" });
    const user = userEvent.setup();
    render(<ChatBar {...props} />);

    await user.click(screen.getByRole("button", { name: "…" }));

    expect(props.onSubmitChat).not.toHaveBeenCalled();
  });

  it("submits on Enter without Shift", async () => {
    const props = defaultProps({ chatInput: "route risk" });
    const user = userEvent.setup();
    render(<ChatBar {...props} />);

    const input = screen.getByLabelText("Chat input");
    await user.click(input);
    await user.keyboard("{Enter}");

    expect(props.onSubmitChat).toHaveBeenCalledTimes(1);
  });

  it("updates knowledge base selection", async () => {
    const props = defaultProps({
      vectorStores: [{ id: "vs_1", name: "Risk KB", status: "completed" }],
    });
    const user = userEvent.setup();
    render(<ChatBar {...props} />);

    await user.selectOptions(screen.getByLabelText("Knowledge base"), "vs_1");

    expect(props.onChangeVectorStore).toHaveBeenCalledWith("vs_1");
  });

  it("shows vector store load errors", () => {
    render(<ChatBar {...defaultProps({ vectorStoresError: "LlamaStack unavailable" })} />);
    expect(screen.getByText("LlamaStack unavailable")).toBeInTheDocument();
  });

  it("renders collapsed preview when messages exist and modal is closed", () => {
    render(
      <ChatBar
        {...defaultProps({
          chatMessages: [
            { role: "human", content: "Hello" },
            { role: "ai", content: "Hi there" },
          ],
        })}
      />,
    );
    expect(document.querySelector('[data-test="chat-collapsed-preview"]')).toBeTruthy();
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("opens the conversation modal from View conversation", async () => {
    const user = userEvent.setup();
    render(
      <ChatBar
        {...defaultProps({
          chatMessages: [{ role: "human", content: "Hello" }],
        })}
      />,
    );

    await user.click(screen.getByRole("button", { name: "View conversation" }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "AI Assistant" })).toBeInTheDocument();
  });

  it("shows completion metadata in the modal for finished assistant turns", async () => {
    const user = userEvent.setup();
    render(
      <ChatBar
        {...defaultProps({
          chatMessages: [
            {
              role: "ai",
              content: "Answer text",
              completion: { model: "meta-llama/Llama-3.2-1B-Instruct", usage: { total_tokens: 42 } },
            },
          ],
        })}
      />,
    );

    await user.click(screen.getByRole("button", { name: "View conversation" }));

    expect(screen.getByText(/42 tokens/)).toBeInTheDocument();
    expect(screen.getByText("Response details")).toBeInTheDocument();
  });

  it("auto-opens the modal when loading finishes with an assistant reply", () => {
    const props = defaultProps({
      chatLoading: true,
      chatMessages: [{ role: "ai", content: "Done" }],
    });
    const { rerender } = render(<ChatBar {...props} />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    rerender(
      <ChatBar
        {...props}
        chatLoading={false}
        chatMessages={[{ role: "ai", content: "Done" }]}
      />,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("closes the modal when dismiss is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ChatBar
        {...defaultProps({
          chatInput: "hi",
          chatMessages: [{ role: "human", content: "Hello" }],
        })}
      />,
    );

    await user.click(screen.getByRole("button", { name: "View conversation" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
