import { DEFAULT_API_BASE_URL, resolveApiBaseUrl } from "../config";

describe("resolveApiBaseUrl", () => {
  it("uses the Jenkins runtime URL first", () => {
    expect(
      resolveApiBaseUrl(
        "https://jenkins.example/backend/",
        "http://vite.local",
      ),
    ).toBe("https://jenkins.example/backend");
  });

  it("uses the Vite URL when Jenkins has not provided one", () => {
    expect(resolveApiBaseUrl(undefined, "http://vite.local/")).toBe(
      "http://vite.local",
    );
  });

  it("uses localhost when no URL is configured", () => {
    expect(resolveApiBaseUrl()).toBe(DEFAULT_API_BASE_URL);
  });

  it("ignores blank values and removes trailing slashes", () => {
    expect(resolveApiBaseUrl("   ", "http://vite.local///")).toBe(
      "http://vite.local",
    );
  });
});
