const isProduction = (): boolean => {
  if (typeof process !== "undefined" && process.env?.NODE_ENV) {
    return process.env.NODE_ENV === "production";
  }
  return false;
};

const getApiBaseUrlFromEnv = (): string | undefined => {
  if (typeof process !== "undefined" && process.env?.VITE_API_BASE_URL) {
    return process.env.VITE_API_BASE_URL;
  }
  return undefined;
};

const getApiBaseUrl = (): string => {
  const envUrl = getApiBaseUrlFromEnv();

  if (envUrl) {
    return envUrl;
  }

  return isProduction() ? "" : "http://localhost:8000";
};

export const API_BASE_URL = getApiBaseUrl();

export const CHATBOT_API_TIMEOUTS_MS = {
  CREATE_SESSION: 3000,
  DELETE_SESSION: 3000,
  GENERATE_MESSAGE: 300000,
};
