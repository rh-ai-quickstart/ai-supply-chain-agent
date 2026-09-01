import { useCallback, useEffect, useRef, useState } from "react";
import { getNews } from "../services/newsService";
import { getLogger } from "../utils/logger.js";

const logger = getLogger(import.meta.url);
const NEWS_POLL_MS = 5 * 60 * 1000;

/**
 * Polls the news headline ticker, extracted from `App.jsx` (SRP). Skips a
 * refresh while chat is streaming so RSS polling doesn't compete with the
 * shared CPU/network budget — `isChatBusy` is read through a ref so the
 * polling effect doesn't need to resubscribe every time chat state changes.
 */
export function useNewsFeed(isChatBusy) {
  const [newsItems, setNewsItems] = useState([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const newsAbortRef = useRef(null);
  const isChatBusyRef = useRef(isChatBusy);
  useEffect(() => {
    isChatBusyRef.current = isChatBusy;
  }, [isChatBusy]);

  const loadNews = useCallback(async () => {
    if (isChatBusyRef.current) return;
    logger.debug("useNewsFeed: loading news");
    newsAbortRef.current?.abort();
    const controller = new AbortController();
    newsAbortRef.current = controller;
    try {
      const res = await getNews({ signal: controller.signal });
      if (controller.signal.aborted) return;
      setNewsItems(Array.isArray(res?.items) ? res.items : []);
      logger.debug("useNewsFeed: loaded %d items", res?.items?.length || 0);
    } catch (err) {
      if (err?.name === "AbortError") return;
      logger.error("useNewsFeed loadNews error: %s", err.message);
      // Keep prior headlines on refresh failure; empty only on first load.
      setNewsItems((prev) => (Array.isArray(prev) ? prev : []));
    } finally {
      if (newsAbortRef.current === controller) {
        newsAbortRef.current = null;
        setNewsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    loadNews();
    const timer = window.setInterval(loadNews, NEWS_POLL_MS);
    return () => {
      window.clearInterval(timer);
      newsAbortRef.current?.abort();
    };
  }, [loadNews]);

  return { newsItems, newsLoading };
}
