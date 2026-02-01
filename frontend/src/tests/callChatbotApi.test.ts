import fetchMock from "jest-fetch-mock";
import { callChatbotApi } from "../utils/callChatbotApi";
import { API_BASE_URL } from "../config";

describe("callChatbotApi", () => {
  beforeEach(() => {
    fetchMock.resetMocks();
    jest.spyOn(console, "error").mockImplementation(() => {});
  });

  it("returns parsed JSON when response is ok", async () => {
    const mockData = { reply: "Hello" };
    fetchMock.mockResponseOnce(JSON.stringify(mockData));

    const result = await callChatbotApi(
      "some-endpoint",
      {},
      { fallback: true },
      5000,
    );

    expect(result).toEqual(mockData);

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/some-endpoint`,
      expect.objectContaining({
        signal: expect.any(Object),
      }),
    );
  });

  it("returns fallback value when response is not ok", async () => {
    fetchMock.mockResponseOnce("Internal error", { status: 500 });

    const fallback = { error: "fallback" };
    const result = await callChatbotApi("bad-endpoint", {}, fallback, 5000);

    expect(result).toBe(fallback);
  });

  it("returns fallback value when fetch throws", async () => {
    fetchMock.mockRejectOnce(new Error("Network error"));

    const fallback = { error: "network" };
    const result = await callChatbotApi("error-endpoint", {}, fallback, 5000);

    expect(result).toBe(fallback);
  });

  it("returns fallback value when request times out (AbortError)", async () => {
    const abortError = { name: "AbortError" };

    fetchMock.mockRejectedValueOnce(abortError);

    const fallback = { error: "timeout" };
    const result = await callChatbotApi("timeout-endpoint", {}, fallback, 10);

    expect(result).toBe(fallback);
  });
});
