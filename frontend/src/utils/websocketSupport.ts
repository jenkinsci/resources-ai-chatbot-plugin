/**
 * Utility functions for WebSocket support detection and URL conversion.
 */

/**
 * Checks if WebSocket is supported in the current browser environment.
 *
 * @returns {boolean} True if WebSocket is available, false otherwise
 */
export const isWebSocketSupported = (): boolean => {
  return typeof WebSocket !== "undefined";
};

/**
 * Converts an HTTP/HTTPS URL to a WebSocket/WSS URL.
 *
 * @param {string} baseUrl - The base URL (e.g., "http://localhost:8000")
 * @returns {string} The WebSocket URL (e.g., "ws://localhost:8000")
 */
export const getWebSocketUrl = (baseUrl: string): string => {
  return baseUrl.replace(/^http/, "ws");
};
