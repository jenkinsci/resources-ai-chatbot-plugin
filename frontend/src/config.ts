type ViteEnv = {
  VITE_API_BASE_URL?: string;
  PROD: boolean;
  DEV: boolean;
  MODE: string;
};

const getEnv = (): ViteEnv => {
  if (typeof import.meta !== "undefined" && (import.meta as any).env) {
    return (import.meta as any).env as ViteEnv;
  }

  return {
    VITE_API_BASE_URL: process.env.VITE_API_BASE_URL,
    PROD: process.env.NODE_ENV === "production",
    DEV: process.env.NODE_ENV !== "production",
    MODE: process.env.NODE_ENV ?? "test",
  };
};

const getApiBaseUrl = (): string => {
  const env = getEnv();

  if (env.VITE_API_BASE_URL) {
    return env.VITE_API_BASE_URL;
  }

  return env.PROD ? "" : "http://localhost:8000";
};

export const API_BASE_URL = getApiBaseUrl();

export const CHATBOT_API_TIMEOUTS_MS = {
  CREATE_SESSION: 3000,
  DELETE_SESSION: 3000,
  GENERATE_MESSAGE: 300000,
};
