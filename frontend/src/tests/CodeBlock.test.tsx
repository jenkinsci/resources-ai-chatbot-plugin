import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CodeBlock } from "../components/CodeBlock";
import * as chatbotApi from "../api/chatbot";

jest.mock("../api/chatbot", () => ({
  validatePipeline: jest.fn(),
}));

describe("CodeBlock component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.assign(navigator, {
      clipboard: {
        writeText: jest.fn().mockImplementation(() => Promise.resolve()),
      },
    });
  });

  it("renders a standard code block with language badge and copy button", () => {
    render(<CodeBlock language="python" code="print('hello')" />);

    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("print('hello')")).toBeInTheDocument();
    expect(screen.getByLabelText("Copy Code")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Validate Pipeline Syntax"),
    ).not.toBeInTheDocument();
  });

  it("renders Jenkinsfile controls when code contains a pipeline block", () => {
    const pipelineCode =
      "pipeline {\n  agent any\n  stages {\n    stage('Build') { steps { sh 'make' } }\n  }\n}";
    render(<CodeBlock language="groovy" code={pipelineCode} />);

    expect(screen.getByText("Jenkinsfile")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Validate Pipeline Syntax"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Download Jenkinsfile")).toBeInTheDocument();
  });

  it("copies code to clipboard when Copy is clicked", async () => {
    render(<CodeBlock language="bash" code="echo 'test'" />);

    const copyBtn = screen.getByLabelText("Copy Code");
    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("echo 'test'");
    await waitFor(() => {
      expect(screen.getByText("Copied!")).toBeInTheDocument();
    });
  });

  it("triggers file download when Download is clicked", () => {
    const pipelineCode = "pipeline { agent any stages {} }";
    const createObjectURLMock = jest.fn().mockReturnValue("blob:mock-url");
    const revokeObjectURLMock = jest.fn();
    globalThis.URL.createObjectURL = createObjectURLMock;
    globalThis.URL.revokeObjectURL = revokeObjectURLMock;

    render(<CodeBlock language="jenkinsfile" code={pipelineCode} />);

    const downloadBtn = screen.getByLabelText("Download Jenkinsfile");
    fireEvent.click(downloadBtn);

    expect(createObjectURLMock).toHaveBeenCalled();
  });

  it("validates pipeline and displays success banner when valid", async () => {
    (chatbotApi.validatePipeline as jest.Mock).mockResolvedValueOnce({
      is_valid: true,
      pipeline_type: "declarative",
      errors: [],
      warnings: [],
      suggestions: ["Add post cleanup"],
      stages: ["Build", "Test"],
    });

    const pipelineCode =
      "pipeline { agent any stages { stage('Build') {} stage('Test') {} } }";
    render(<CodeBlock language="groovy" code={pipelineCode} />);

    const validateBtn = screen.getByLabelText("Validate Pipeline Syntax");
    fireEvent.click(validateBtn);

    await waitFor(() => {
      expect(
        screen.getByText("✅ Valid DECLARATIVE Pipeline"),
      ).toBeInTheDocument();
      expect(screen.getByText(/Stages: Build ➔ Test/)).toBeInTheDocument();
      expect(screen.getByText(/Add post cleanup/)).toBeInTheDocument();
    });
  });

  it("validates pipeline and displays error banner when invalid", async () => {
    (chatbotApi.validatePipeline as jest.Mock).mockResolvedValueOnce({
      is_valid: false,
      pipeline_type: "declarative",
      errors: ["Missing required 'agent' directive."],
      warnings: [],
      suggestions: [],
      stages: [],
    });

    render(<CodeBlock language="groovy" code="pipeline { stages {} }" />);

    const validateBtn = screen.getByLabelText("Validate Pipeline Syntax");
    fireEvent.click(validateBtn);

    await waitFor(() => {
      expect(
        screen.getByText("❌ Pipeline Syntax Issues Found"),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Missing required 'agent' directive/),
      ).toBeInTheDocument();
    });
  });
});
