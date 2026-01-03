const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl !== undefined && envUrl !== '') {
    return envUrl;
  }
  
  return import.meta.env.PROD ? '' : 'http://localhost:8000';
};

export const API_BASE_URL = getApiBaseUrl();

export const CHATBOT_API_TIMEOUTS_MS = {
  CREATE_SESSION: 3000,
  DELETE_SESSION: 3000,
  GENERATE_MESSAGE: 300000,
};
