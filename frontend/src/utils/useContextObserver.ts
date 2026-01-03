import { useState, useEffect } from "react";

/**
 * Custom hook to monitor the user's context (URL and Scroll).
 * Triggers a toast if the user is on a console page and scrolling
 * to the bottom (likely looking at an error).
 */
export const useContextObserver = (isChatOpen: boolean) => {
  const [showToast, setShowToast] = useState(false);
  const [toastTimer, setToastTimer] = useState<ReturnType<
    typeof setTimeout
  > | null>(null);

  useEffect(() => {
    const checkContext = () => {
      // 1. URL Check
      const currentUrl = window.location.href;
      const isConsolePage = currentUrl.includes("/console");

      // Debug log (remove later)
      console.log(
        "[Chatbot Observer] URL:",
        currentUrl,
        "| Is Console:",
        isConsolePage,
      );

      if (!isConsolePage) {
        setShowToast(false);
        return;
      }

      // 2. Scroll Check
      // We use document.documentElement.scrollHeight for better cross-browser compatibility
      const scrollPosition = window.innerHeight + window.scrollY;
      const pageHeight = document.documentElement.scrollHeight;
      const buffer = 150; // Increased buffer to 150px

      const isAtBottom = scrollPosition >= pageHeight - buffer;

      // Debug log (remove later)
      console.log(
        `[Chatbot Observer] Scroll: ${Math.round(scrollPosition)} / ${pageHeight} | At Bottom: ${isAtBottom}`,
      );

      if (isAtBottom && !isChatOpen && !showToast) {
        if (!toastTimer) {
          console.log("[Chatbot Observer] ⏳ Starting timer for toast...");
          const timer = setTimeout(() => {
            console.log("[Chatbot Observer] 🔔 Triggering Toast!");
            setShowToast(true);
          }, 2000); // 2 seconds
          setToastTimer(timer);
        }
      } else {
        if (toastTimer) {
          console.log("[Chatbot Observer] ❌ Condition lost, clearing timer.");
          clearTimeout(toastTimer);
          setToastTimer(null);
        }
      }
    };

    // Run once immediately on mount (in case page is short or already scrolled)
    checkContext();

    // Run on every scroll event
    window.addEventListener("scroll", checkContext);

    return () => {
      window.removeEventListener("scroll", checkContext);
      if (toastTimer) clearTimeout(toastTimer);
    };
  }, [isChatOpen, showToast, toastTimer]);

  return { showToast, setShowToast };
};
