import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatMarkdownBody } from "./ChatMarkdownBody";

vi.mock("react-markdown", () => ({
  default: ({ children }) => <div data-testid="md-body">{children}</div>,
}));

describe("ChatMarkdownBody", () => {
  it("applies compact class when requested", () => {
    const { container } = render(<ChatMarkdownBody content="# Title" compact />);
    expect(container.querySelector(".chat-md--compact")).toBeTruthy();
    expect(screen.getByTestId("md-body")).toHaveTextContent("# Title");
  });

  it("renders plain text while streaming without markdown", () => {
    const { container } = render(<ChatMarkdownBody content="partial" streaming />);
    expect(container.querySelector(".chat-md-plain")).toBeTruthy();
    expect(container.querySelector(".chat-stream-cursor")).toBeTruthy();
    expect(screen.queryByTestId("md-body")).toBeNull();
    expect(screen.getByText(/partial/)).toBeInTheDocument();
  });
});
