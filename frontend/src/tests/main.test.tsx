const renderMock = jest.fn();
const createRootMock = jest.fn(() => ({
  render: renderMock,
}));

jest.mock("react-dom/client", () => ({
  createRoot: createRootMock,
}));

jest.mock("../components/Chatbot", () => ({
  Chatbot: () => <div>Mock Chatbot</div>,
}));

describe("frontend entrypoint", () => {
  beforeEach(() => {
    jest.resetModules();
    renderMock.mockClear();
    createRootMock.mockClear();
    document.body.innerHTML = "";
  });

  it("mounts the chatbot into the plugin footer root", async () => {
    document.body.innerHTML = '<div id="chatbot-root"></div>';

    await import("../main");

    expect(createRootMock).toHaveBeenCalledWith(
      document.getElementById("chatbot-root"),
    );
    expect(renderMock).toHaveBeenCalledTimes(1);
  });

  it("throws a clear error when the plugin footer root is missing", async () => {
    await expect(import("../main")).rejects.toThrow(
      "Chatbot root element '#chatbot-root' was not found.",
    );
  });
});
