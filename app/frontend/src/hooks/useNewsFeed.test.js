import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useNewsFeed } from "./useNewsFeed";

const getNews = vi.hoisted(() => vi.fn());

vi.mock("../services/newsService", () => ({
  getNews: (...args) => getNews(...args),
}));

describe("useNewsFeed", () => {
  beforeEach(() => {
    getNews.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("loads news on mount", async () => {
    getNews.mockResolvedValue({ items: [{ title: "A" }] });
    const { result } = renderHook(() => useNewsFeed(false));
    await waitFor(() => expect(result.current.newsLoading).toBe(false));
    expect(result.current.newsItems).toEqual([{ title: "A" }]);
  });

  it("skips loading while chat is busy", async () => {
    getNews.mockResolvedValue({ items: [{ title: "A" }] });
    const { result } = renderHook(() => useNewsFeed(true));
    await Promise.resolve();
    expect(getNews).not.toHaveBeenCalled();
    expect(result.current.newsLoading).toBe(true);
  });

  it("keeps prior headlines when a later poll fails", async () => {
    vi.useFakeTimers();
    getNews.mockResolvedValueOnce({ items: [{ title: "A" }] });
    const { result } = renderHook(() => useNewsFeed(false));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.newsItems).toEqual([{ title: "A" }]);

    getNews.mockRejectedValueOnce(new Error("boom"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60 * 1000);
    });
    expect(result.current.newsItems).toEqual([{ title: "A" }]);
  });

  it("re-checks the busy flag on every poll without resubscribing the interval", async () => {
    vi.useFakeTimers();
    getNews.mockResolvedValue({ items: [{ title: "A" }] });
    const { result, rerender } = renderHook(({ busy }) => useNewsFeed(busy), {
      initialProps: { busy: false },
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(getNews).toHaveBeenCalledTimes(1);

    rerender({ busy: true });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60 * 1000);
    });
    expect(getNews).toHaveBeenCalledTimes(1);
    expect(result.current.newsItems).toEqual([{ title: "A" }]);
  });
});
