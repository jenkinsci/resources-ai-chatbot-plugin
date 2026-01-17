export interface JenkinsConfig {
  baseUrl: string;
  crumbFieldName: string;
  crumbToken: string;
  userId: string;
  userName: string;
}
declare global {
  interface Window {
    jenkinsChatbotConfig?: JenkinsConfig;
  }
}

const jenkinsConfig = window.jenkinsChatbotConfig;
export const API_BASE_URL =
  jenkinsConfig?.baseUrl || "http://localhost:8000/api/chatbot";
export const CHATBOT_API_TIMEOUTS_MS = {
  CREATE_SESSION: 3000,
  DELETE_SESSION: 3000,
  GENERATE_MESSAGE: 300000,
};
