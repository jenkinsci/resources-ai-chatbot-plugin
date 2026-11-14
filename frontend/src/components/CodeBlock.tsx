import React, { useState } from "react";
import { chatbotStyles } from "../styles/styles";
import {
  validatePipeline,
  type PipelineValidationResponse,
} from "../api/chatbot";
import { Check, Copy, Download, PlayCircle } from "lucide-react";

interface CodeBlockProps {
  language: string;
  code: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] =
    useState<PipelineValidationResponse | null>(null);

  const isJenkinsPipeline =
    language.toLowerCase() === "jenkinsfile" ||
    language.toLowerCase() === "groovy" ||
    code.includes("pipeline {") ||
    code.includes("pipeline{") ||
    code.includes("node {") ||
    code.includes("node{");

  const displayLanguage = isJenkinsPipeline
    ? "Jenkinsfile"
    : language || "Code";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is not available
      setCopied(false);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = isJenkinsPipeline ? "Jenkinsfile" : "script.txt";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const result = await validatePipeline(code);
      setValidationResult(result);
    } catch {
      setValidationResult({
        is_valid: false,
        pipeline_type: "unknown",
        errors: ["Failed to connect to validation service."],
        warnings: [],
        suggestions: [],
        stages: [],
      });
    } finally {
      setValidating(false);
    }
  };

  return (
    <div style={chatbotStyles.codeBlockContainer} data-testid="code-block">
      <div style={chatbotStyles.codeBlockHeader}>
        <span style={chatbotStyles.codeBlockLanguage}>{displayLanguage}</span>
        <div style={chatbotStyles.codeBlockActionGroup}>
          {isJenkinsPipeline && (
            <>
              <button
                type="button"
                onClick={handleValidate}
                disabled={validating}
                style={chatbotStyles.codeBlockButton}
                aria-label="Validate Pipeline Syntax"
              >
                <PlayCircle size={13} aria-hidden="true" />
                <span>{validating ? "Checking..." : "Validate"}</span>
              </button>
              <button
                type="button"
                onClick={handleDownload}
                style={chatbotStyles.codeBlockButton}
                aria-label="Download Jenkinsfile"
              >
                <Download size={13} aria-hidden="true" />
                <span>Download</span>
              </button>
            </>
          )}
          <button
            type="button"
            onClick={handleCopy}
            style={chatbotStyles.codeBlockButton}
            aria-label="Copy Code"
          >
            {copied ? (
              <>
                <Check size={13} aria-hidden="true" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy size={13} aria-hidden="true" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      <pre style={chatbotStyles.codeBlockContent}>
        <code>{code}</code>
      </pre>

      {validationResult && (
        <div
          style={chatbotStyles.validationBanner(validationResult.is_valid)}
          data-testid="validation-result"
        >
          <strong>
            {validationResult.is_valid
              ? `✅ Valid ${validationResult.pipeline_type.toUpperCase()} Pipeline`
              : "❌ Pipeline Syntax Issues Found"}
          </strong>
          {validationResult.stages.length > 0 && (
            <span>Stages: {validationResult.stages.join(" ➔ ")}</span>
          )}
          {validationResult.errors.map((err, idx) => (
            <span key={`err-${idx}`}>• Error: {err}</span>
          ))}
          {validationResult.warnings.map((warn, idx) => (
            <span key={`warn-${idx}`}>• Warning: {warn}</span>
          ))}
          {validationResult.suggestions.map((sug, idx) => (
            <span key={`sug-${idx}`}>💡 Suggestion: {sug}</span>
          ))}
        </div>
      )}
    </div>
  );
};
