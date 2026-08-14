import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { InfoTooltip } from "./InfoTooltip";

describe("InfoTooltip", () => {
  it("renders a help trigger and shows tooltip text on hover", async () => {
    const user = userEvent.setup();
    render(<InfoTooltip label="About news" content="Headlines from RSS feeds." />);
    expect(screen.getByRole("button", { name: "About news" })).toBeInTheDocument();
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    await user.hover(screen.getByRole("button", { name: "About news" }));
    expect(screen.getByRole("tooltip")).toHaveTextContent("Headlines from RSS feeds.");
    expect(screen.getByRole("tooltip")).toHaveClass("info-tooltip__content--portal");
  });

  it("shows tooltip text on keyboard focus", () => {
    render(<InfoTooltip label="About map view" content="Map view help." />);
    fireEvent.focus(screen.getByRole("button", { name: "About map view" }));
    expect(screen.getByRole("tooltip")).toHaveTextContent("Map view help.");
  });

  it("renders nothing when content is empty", () => {
    const { container } = render(<InfoTooltip label="Empty" content="   " />);
    expect(container).toBeEmptyDOMElement();
  });
});
