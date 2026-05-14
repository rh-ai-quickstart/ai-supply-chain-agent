import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AlertsPanel } from "./AlertsPanel";

describe("AlertsPanel", () => {
  it("shows loading copy while loading", () => {
    render(<AlertsPanel loading error="" alerts={[]} />);
    expect(screen.getByText(/loading live state/i)).toBeInTheDocument();
  });

  it("shows error message when provided", () => {
    render(<AlertsPanel loading={false} error="Backend down" alerts={[]} />);
    expect(screen.getByText("Backend down")).toBeInTheDocument();
  });

  it("renders up to six alerts with type labels", () => {
    const alerts = Array.from({ length: 8 }, (_, i) => ({
      type: i % 2 === 0 ? "info" : "warn",
      text: `msg-${i}`,
    }));
    render(<AlertsPanel loading={false} error="" alerts={alerts} />);
    expect(screen.getByText(/msg-0/i)).toBeInTheDocument();
    expect(screen.getByText(/msg-5/i)).toBeInTheDocument();
    expect(screen.queryByText(/msg-6/i)).not.toBeInTheDocument();
  });
});
