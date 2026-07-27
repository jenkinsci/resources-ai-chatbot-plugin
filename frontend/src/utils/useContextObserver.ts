import { useEffect, useState } from "react";

interface BuildStatusResponse {
  result: string | null;
}

const buildStatusUrl = (): string => {
  const buildPath = window.location.pathname.replace(/\/console\/?$/, "");
  return `${window.location.origin}${buildPath}/api/json?tree=result`;
};

/**
 * Shows the log-analysis toast for a failed Jenkins build console.
 */
export const useContextObserver = (isChatOpen: boolean) => {
  const [showToast, setShowToast] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const clearTimer = () => {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
    };

    const loadBuildStatus = async () => {
      setShowToast(false);

      if (isChatOpen || !window.location.pathname.includes("/console")) {
        return;
      }

      try {
        const response = await fetch(buildStatusUrl(), {
          credentials: "same-origin",
        });
        if (!response.ok) {
          return;
        }

        const status = (await response.json()) as BuildStatusResponse;
        if (cancelled || status.result !== "FAILURE") {
          return;
        }

        timer = setTimeout(() => {
          setShowToast(true);
          timer = null;
        }, 2000);
      } catch {
        setShowToast(false);
      }
    };

    loadBuildStatus();

    return () => {
      cancelled = true;
      clearTimer();
    };
  }, [isChatOpen]);

  return { showToast, setShowToast };
};
