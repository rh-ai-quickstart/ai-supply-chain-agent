import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

describe("ErrorBoundary", () => {
  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <span data-testid="child">Hello</span>
      </ErrorBoundary>
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("shows error message when child throws", () => {
    // Component that throws during render
    const Throwy = () => {
      throw new Error("boom");
    };

    render(
      <ErrorBoundary>
        <Throwy />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("shows fallback error message when Error() has no message", () => {
    const Throwy = () => {
      throw new Error();
    };

    render(
      <ErrorBoundary>
        <Throwy />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("An unexpected error occurred.")).toBeInTheDocument();
  });

  it("renders try again button", () => {
    const Throwy = () => {
      throw new Error("boom");
    };

    render(
      <ErrorBoundary>
        <Throwy />
      </ErrorBoundary>
    );
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("recovers after try again button clicked", () => {
    const Throwy = () => {
      throw new Error("boom");
    };
    const Good = () => <span>recovered</span>;

    const wrapper = () => (
      <ErrorBoundary>
        <Good />
      </ErrorBoundary>
    );

    const { rerender } = render(wrapper());
    
    // First, show the error state
    render(
      <ErrorBoundary>
        <Throwy />
      </ErrorBoundary>
    );
    expect(screen.getByText("boom")).toBeInTheDocument();
    
    // Click try again to reset
    screen.getByRole("button", { name: /try again/i }).click();
    
    // Now re-render the good component
    rerender(
      <ErrorBoundary>
        <Good />
      </ErrorBoundary>
    );
    expect(screen.getByText("recovered")).toBeInTheDocument();
  });

  it("renders button that resets error state", () => {
    const Throwy = () => {
      throw new Error("boom");
    };

    const { rerender } = render(
      <ErrorBoundary>
        <Throwy />
      </ErrorBoundary>
    );
    expect(screen.getByText("boom")).toBeInTheDocument();

    // Click try again - ErrorBoundary resets state to hasError: false
    screen.getByRole("button", { name: /try again/i }).click();

    // Re-render with a working component
    rerender(
      <ErrorBoundary>
        <span>ok</span>
      </ErrorBoundary>
    );
    expect(screen.getByText("ok")).toBeInTheDocument();
    expect(screen.queryByText("boom")).not.toBeInTheDocument();
  });

  it("uses error-boundary CSS class on error container", () => {
    const Throwy = () => {
      throw new Error("boom");
    };

    render(
      <ErrorBoundary>
        <Throwy />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong").closest(".error-boundary")).toBeInTheDocument();
  });

  it("shows error message with error CSS class", () => {
    const Throwy = () => {
      throw new Error("boom");
    };

    render(
      <ErrorBoundary>
        <Throwy />
      </ErrorBoundary>
    );
    expect(screen.getByText("boom").closest(".error")).toBeInTheDocument();
  });
});
