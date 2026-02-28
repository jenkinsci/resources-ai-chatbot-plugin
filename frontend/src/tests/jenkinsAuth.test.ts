/**
 * Tests for Jenkins configuration and CSRF token handling
 */

import { describe, it, expect, beforeEach, afterEach } from "@jest/globals";

/* eslint-disable @typescript-eslint/no-explicit-any */

describe("Jenkins Configuration", () => {
  let originalJenkinsConfig: any;

  beforeEach(() => {
    // Save original config
    originalJenkinsConfig = (window as any).jenkinsConfig;
    // Clear module cache before each test to allow fresh imports
    jest.resetModules();
  });

  afterEach(() => {
    // Restore original config
    (window as any).jenkinsConfig = originalJenkinsConfig;
    // Clear module cache after each test
    jest.resetModules();
  });

  it("should use Jenkins config when available", async () => {
    // Mock Jenkins config
    (window as any).jenkinsConfig = {
      rootURL: "https://jenkins.example.com",
      apiBaseURL: "https://jenkins.example.com/chatbot",
      crumb: "Jenkins-Crumb",
      crumbValue: "test-crumb-value-123",
    };

    // Dynamically import config to get the values based on mocked window object
    const {
      API_BASE_URL,
      JENKINS_CRUMB_FIELD,
      JENKINS_CRUMB_VALUE,
      JENKINS_ROOT_URL,
    } = await import("../config");

    expect(API_BASE_URL).toBe("https://jenkins.example.com/chatbot");
    expect(JENKINS_CRUMB_FIELD).toBe("Jenkins-Crumb");
    expect(JENKINS_CRUMB_VALUE).toBe("test-crumb-value-123");
    expect(JENKINS_ROOT_URL).toBe("https://jenkins.example.com");
  });

  it("should fall back to localhost when Jenkins config is unavailable", async () => {
    // Ensure Jenkins config is not set
    delete (window as any).jenkinsConfig;

    const { API_BASE_URL, JENKINS_CRUMB_FIELD, JENKINS_CRUMB_VALUE } =
      await import("../config");

    expect(API_BASE_URL).toBe("http://localhost:8000");
    expect(JENKINS_CRUMB_FIELD).toBe("");
    expect(JENKINS_CRUMB_VALUE).toBe("");
  });
});

describe("CSRF Token Handling in API Calls", () => {
  let originalFetch: typeof fetch;

  beforeEach(() => {
    // Clear module cache before each test to ensure fresh imports
    jest.resetModules();

    // Mock Jenkins config with CSRF token
    (window as any).jenkinsConfig = {
      rootURL: "https://jenkins.example.com",
      apiBaseURL: "https://jenkins.example.com/chatbot",
      crumb: "Jenkins-Crumb",
      crumbValue: "secure-token-456",
    };

    // Save original fetch and mock it
    originalFetch = globalThis.fetch;
    globalThis.fetch = jest.fn() as any;
  });

  afterEach(() => {
    // Restore original fetch
    globalThis.fetch = originalFetch;
    jest.restoreAllMocks();
    // Clear module cache after each test
    jest.resetModules();
  });

  it("should include CSRF token in request headers", async () => {
    const mockFetch = globalThis.fetch as jest.Mock;
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: "test-session" }),
    });

    const { callChatbotApi } = await import("../utils/callChatbotApi");

    await callChatbotApi(
      "sessions",
      { method: "POST" },
      { session_id: "" },
      3000,
    );

    // Verify fetch was called with CSRF token
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("sessions"),
      expect.objectContaining({
        headers: expect.objectContaining({
          "Jenkins-Crumb": "secure-token-456",
        }),
        credentials: "same-origin",
      }),
    );
  });

  it("should include credentials in all API requests", async () => {
    const mockFetch = globalThis.fetch as jest.Mock;
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ reply: "test reply" }),
    });

    const { callChatbotApi } = await import("../utils/callChatbotApi");

    await callChatbotApi(
      "sessions/123/message",
      { method: "POST", headers: { "Content-Type": "application/json" } },
      {},
      300000,
    );

    // Verify credentials are included
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        credentials: "same-origin",
      }),
    );
  });
});
