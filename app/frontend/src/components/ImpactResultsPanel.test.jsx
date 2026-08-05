import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QUERY_RESPONSE_FIXTURE } from "../test/fixtures/queryResponse";
import { ImpactResultsPanel } from "./ImpactResultsPanel";

vi.mock("./ChatMarkdownBody.jsx", () => ({
  ChatMarkdownBody: ({ content }) => <div data-testid="markdown">{content}</div>,
}));

describe("ImpactResultsPanel", () => {
  it("shows empty state when no result", () => {
    render(<ImpactResultsPanel />);
    expect(screen.getByText(/Run a query to see impact score/i)).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(<ImpactResultsPanel loading />);
    expect(screen.getByText(/Waiting for solver response/i)).toBeInTheDocument();
  });

  it("renders KPIs, answer, options, breakdown, and trace from QueryResponse", () => {
    render(<ImpactResultsPanel result={QUERY_RESPONSE_FIXTURE} />);

    expect(screen.getByText("0.650")).toBeInTheDocument();
    expect(screen.getByText(/1,234,567|\$1,234,567/)).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "Three aircraft are affected by the UK airspace closure.",
    );
    expect(screen.getByText(/emergency_response/i)).toBeInTheDocument();
    expect(screen.getAllByText(/opensky-407290/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Tool call trace \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Affected entities \(3\)/i)).toBeInTheDocument();
  });
});
