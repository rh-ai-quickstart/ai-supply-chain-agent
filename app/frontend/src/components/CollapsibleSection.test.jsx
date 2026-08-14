import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { CollapsibleSection } from "./CollapsibleSection";

describe("CollapsibleSection", () => {
  it("hides content by default and expands on click", async () => {
    const user = userEvent.setup();
    render(
      <CollapsibleSection title="Response options">
        <p>Option details</p>
      </CollapsibleSection>,
    );

    expect(screen.getByRole("button", { name: /Response options/i })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.queryByText("Option details")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Response options/i }));
    expect(screen.getByRole("button", { name: /Response options/i })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByText("Option details")).toBeInTheDocument();
  });

  it("can start open when defaultOpen is true", () => {
    render(
      <CollapsibleSection title="Answer" defaultOpen>
        <p>Summary text</p>
      </CollapsibleSection>,
    );
    expect(screen.getByText("Summary text")).toBeInTheDocument();
  });
});
