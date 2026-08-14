import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QUERY_RESPONSE_FIXTURE } from "../test/fixtures/queryResponse";
import { ImpactResultsPanel } from "./ImpactResultsPanel";

vi.mock("./ChatMarkdownBody.jsx", () => ({
  ChatMarkdownBody: ({ content }) => <div data-testid="markdown">{content}</div>,
}));

async function expandSection(labelPattern) {
  const trigger = sectionTrigger(labelPattern);
  if (!trigger) {
    throw new Error(`Collapsible section not found: ${labelPattern}`);
  }
  await userEvent.click(trigger);
}

function sectionTrigger(labelPattern) {
  return screen
    .getAllByRole("button")
    .find(
      (button) =>
        button.classList.contains("collapsible-section__trigger") &&
        new RegExp(labelPattern, "i").test(button.textContent || ""),
    );
}

describe("ImpactResultsPanel", () => {
  it("shows empty state when no result", () => {
    render(<ImpactResultsPanel />);
    expect(screen.getByText(/Select a scenario to see impact score/i)).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(<ImpactResultsPanel loading />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(document.querySelector(".loading-spinner")).toBeInTheDocument();
    expect(screen.getByText(/Analyzing impact/i)).toBeInTheDocument();
  });

  it("renders KPIs, answer, options, breakdown, and trace from QueryResponse", async () => {
    render(<ImpactResultsPanel result={QUERY_RESPONSE_FIXTURE} />);

    expect(screen.getByText("0.650")).toBeInTheDocument();
    expect(screen.getByText(/1,234,567|\$1,234,567/)).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /About response options/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /About recommended diversions/i })).toBeInTheDocument();

    expect(sectionTrigger("^Answer$")).toBeTruthy();
    expect(sectionTrigger("Response options")).toBeTruthy();
    expect(sectionTrigger("Recommended diversions")).toBeTruthy();
    expect(sectionTrigger("Affected entities")).toBeTruthy();
    expect(sectionTrigger("Tool call trace")).toBeTruthy();

    await expandSection("Answer");
    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "Three aircraft are affected by the UK airspace closure.",
    );

    await expandSection("Response options");
    expect(screen.getByText(/emergency_response/i)).toBeInTheDocument();

    await expandSection("Recommended diversions");
    expect(screen.getByRole("button", { name: /opensky-407290.*Dublin/i })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /opensky-407290/ }).length).toBeGreaterThan(0);
  });

  it("strips duplicate diversion lists from the answer when structured reroutes exist", async () => {
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

    await expandSection("Answer");
    const answer = screen.getByTestId("markdown");
    expect(answer).toHaveTextContent("Affected Aircraft");
    expect(answer).toHaveTextContent("BAW442 - Route: LHR-JFK");
    expect(answer).not.toHaveTextContent("Recommended Diversions");
    expect(answer).not.toHaveTextContent("USD 1,234,567 at risk");
    await expandSection("Recommended diversions");
    expect(screen.getByRole("button", { name: /opensky-407290.*Dublin/i })).toBeInTheDocument();
  });

  it("calls onFocusEntity when an affected entity link is clicked", async () => {
    const onFocusEntity = vi.fn();
    render(
      <ImpactResultsPanel result={QUERY_RESPONSE_FIXTURE} onFocusEntity={onFocusEntity} />,
    );

    await expandSection("Affected entities");
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

    await expandSection("Recommended diversions");
    await userEvent.click(screen.getByRole("button", { name: /opensky-407290.*Dublin/i }));
    expect(onFocusDiversion).toHaveBeenCalledWith(
      expect.objectContaining({
        entity_id: "opensky-407290",
        target_id: "EIDW",
        target_label: "Dublin (EIDW)",
      }),
    );
  });

  it("keeps result sections collapsed by default for quick scanning", () => {
    render(<ImpactResultsPanel result={QUERY_RESPONSE_FIXTURE} />);

    expect(sectionTrigger("^Answer$")).toHaveAttribute("aria-expanded", "false");
    expect(sectionTrigger("Response options")).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("markdown")).not.toBeInTheDocument();
  });
});
