import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NewsTicker } from "./NewsTicker";

describe("NewsTicker", () => {
  it("renders headline titles as links", () => {
    render(
      <NewsTicker
        items={[
          {
            title: "Port strike disrupts shipping",
            link: "https://example.com/1",
            source: "BBC",
          },
        ]}
      />,
    );
    const links = screen.getAllByRole("link", { name: /Port strike disrupts shipping/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    expect(links[0]).toHaveAttribute("href", "https://example.com/1");
    expect(screen.getByText("News")).toBeInTheDocument();
  });

  it("shows quiet empty state when there are no headlines", () => {
    render(<NewsTicker items={[]} loading={false} />);
    expect(screen.getByText(/No headlines available/i)).toBeInTheDocument();
  });

  it("shows loading text while waiting for first fetch", () => {
    render(<NewsTicker items={[]} loading={true} />);
    expect(screen.getAllByText(/Loading latest headlines/i).length).toBeGreaterThan(0);
  });
});
