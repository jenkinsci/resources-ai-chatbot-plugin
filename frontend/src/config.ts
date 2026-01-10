// Jenkins configuration interface
interface JenkinsConfig {
  rootURL: string;
  apiBaseURL: string;
  crumb: string;
  crumbValue: string;
}

// Type assertion for window.jenkinsConfig
declare global {
  interface Window {
    jenkinsConfig?: JenkinsConfig;
  }
}

// Read configuration from Jenkins-injected window.jenkinsConfig
// Falls back to localhost for development
export const API_BASE_URL =
  window.jenkinsConfig?.apiBaseURL || "http://localhost:8000";

export const JENKINS_CRUMB_FIELD = window.jenkinsConfig?.crumb || "";

export const JENKINS_CRUMB_VALUE = window.jenkinsConfig?.crumbValue || "";

export const JENKINS_ROOT_URL = window.jenkinsConfig?.rootURL || "";

export const CHATBOT_API_TIMEOUTS_MS = {
  CREATE_SESSION: 3000,
  DELETE_SESSION: 3000,
  GENERATE_MESSAGE: 300000,
};
