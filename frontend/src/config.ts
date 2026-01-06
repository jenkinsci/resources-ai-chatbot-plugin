interface JenkinsConfig {
  baseUrl: string;
  crumbFieldName: string;
  crumbToken: string;
}
const jenkinsConfig = (window as any).jenkinsChatbotConfig as
  | JenkinsConfig
  | undefined;
export const API_BASE_URL = jenkinsConfig
  ? jenkinsConfig.baseUrl
  : "http://localhost:8000";
export const CHATBOT_API_TIMEOUTS_MS = {
  CREATE_SESSION: 3000,
  DELETE_SESSION: 3000,
  GENERATE_MESSAGE: 300000,
};
