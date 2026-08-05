import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    expect(screen.getByText(/Recommended Diversions/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /opensky-407290.*Dublin/i })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /opensky-407290/ }).length).toBeGreaterThan(0);
    expect(screen.getByText(/Tool call trace \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Affected entities \(3\)/i)).toBeInTheDocument();
  });

  it("strips duplicate diversion lists from the answer when structured reroutes exist", () => {
    const result = {
      ...QUERY_RESPONSE_FIXTURE,
      answer: [
        "Affected Aircraft",
        "BAW442 - Route: LHR-JFK",
        "",
        "Recommended Diversions",
        "BAW442 (LHR-JFK) → Dublin (EIDW)",
        "",
        "Estimated Cost of Impact",
        "USD 1,234,567 at risk.",
      ].join("\n"),
    };
    render(<ImpactResultsPanel result={result} />);

    const answer = screen.getByTestId("markdown");
    expect(answer).toHaveTextContent("Affected Aircraft");
    expect(answer).toHaveTextContent("BAW442 - Route: LHR-JFK");
    expect(answer).not.toHaveTextContent("Recommended Diversions");
    expect(answer).not.toHaveTextContent("USD 1,234,567 at risk");
    expect(screen.getByRole("button", { name: /opensky-407290.*Dublin/i })).toBeInTheDocument();
  });

  it("calls onFocusEntity when an affected entity link is clicked", async () => {
    const onFocusEntity = vi.fn();
    render(
      <ImpactResultsPanel result={QUERY_RESPONSE_FIXTURE} onFocusEntity={onFocusEntity} />,
    );

    await userEvent.click(screen.getByRole("button", { name: "opensky-471f52" }));
    expect(onFocusEntity).toHaveBeenCalledWith("opensky-471f52");
  });

  it("calls onFocusDiversion when a recommended diversion is clicked", async () => {
    const onFocusDiversion = vi.fn();
    render(
      <ImpactResultsPanel
        result={QUERY_RESPONSE_FIXTURE}
        onFocusDiversion={onFocusDiversion}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /opensky-407290.*Dublin/i }));
    expect(onFocusDiversion).toHaveBeenCalledWith(
      expect.objectContaining({
        entity_id: "opensky-407290",
        target_id: "EIDW",
        target_label: "Dublin (EIDW)",
      }),
    );
  });
});
