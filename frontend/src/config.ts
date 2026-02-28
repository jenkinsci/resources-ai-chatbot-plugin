export const API_BASE_URL = "http://localhost:8000";
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");
export const CHATBOT_API_TIMEOUTS_MS = {
  CREATE_SESSION: 3000,
  DELETE_SESSION: 3000,
  GENERATE_MESSAGE: 300000,
};
