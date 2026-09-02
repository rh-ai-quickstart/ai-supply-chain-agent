import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SectionHeading } from "./SectionHeading";

describe("SectionHeading", () => {
  it("renders the title", () => {
    render(<SectionHeading id="impact-map">Impact map</SectionHeading>);
    expect(screen.getByRole("heading", { name: "Impact map" })).toHaveAttribute(
      "id",
      "impact-map",
    );
  });

  it("renders an info tooltip when provided", () => {
    render(
      <SectionHeading id="scenarios" tooltip="Choose a disruption scenario.">
        Scenario selection
      </SectionHeading>,
    );
    expect(
      screen.getByRole("button", { name: "About Scenario selection" }),
    ).toBeInTheDocument();
  });

  it("omits tooltip when not provided", () => {
    render(<SectionHeading>Overview</SectionHeading>);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
