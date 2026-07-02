/**
 * API configuration with environment variable support.
 * For development: defaults to localhost:8000
 * For production: set REACT_APP_API_BASE_URL environment variable
 * 
 * Example:
 * REACT_APP_API_BASE_URL=https://api.example.com npm run build
 */
export const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

/**
 * Timeout configurations for API operations (in milliseconds).
 * These can be adjusted based on network conditions and server performance.
 * - CREATE_SESSION: 3000ms (3 seconds) for session creation
 * - DELETE_SESSION: 3000ms (3 seconds) for session deletion  
 * - GENERATE_MESSAGE: 30000ms (30 seconds) for message generation
 *   Note: Reduced from 5 minutes to prevent client timeouts on slow connections
 */
export const CHATBOT_API_TIMEOUTS_MS = {
  CREATE_SESSION: 3000,
  DELETE_SESSION: 3000,
  GENERATE_MESSAGE: 30000, // Reduced from 300000 (5 min) to 30 seconds for better UX
};
