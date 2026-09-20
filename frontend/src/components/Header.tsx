import { getChatbotText } from "../data/chatbotTexts";
import { chatbotStyles } from "../styles/styles";
import {
  exportAsTxt,
  exportAsMd,
  exportAsDocx,
  exportAsPdf,
} from "../utils/exportchat";
import type { Message } from "../model/Message";
import type { ProviderMetadata } from "../api/chatbot";
import {
  type KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Upload,
  Trash2,
  FileText,
  FileCode,
  FileSpreadsheet,
  File,
  Check,
  ChevronDown,
  TriangleAlert,
} from "lucide-react";

/**
 * Props for the Header component.
 */
export interface HeaderProps {
  currentSessionId: string | null;
  clearMessages: (chatSessionId: string) => void;
  openSideBar: () => void;
  messages: Message[];
  providers?: ProviderMetadata[];
  selectedProviderId?: string;
  onProviderChange?: (providerId: string) => void;
}

const PROVIDER_LOGOS: Record<string, string> = {
  anthropic: "/icons/providers/anthropic.svg",
  gemini: "/icons/providers/gemini.svg",
  groq: "/icons/providers/groq.svg",
  local: "/icons/providers/mistral.svg",
  mistral: "/icons/providers/mistral.svg",
  mistralai: "/icons/providers/mistral.svg",
  openai: "/icons/providers/chatgpt.svg",
  openrouter: "/icons/providers/openrouter.svg",
};

const getProviderInitial = (label: string, providerId: string): string => {
  const providerName = label.trim() || providerId.trim();
  return providerName.charAt(0).toUpperCase() || "?";
};

const ProviderIcon = ({
  providerId,
  label,
}: {
  providerId: string;
  label: string;
}) => {
  const logoSource = PROVIDER_LOGOS[providerId.toLowerCase()];

  return (
    <span style={chatbotStyles.providerOptionIcon} aria-hidden="true">
      {logoSource ? (
        <img src={logoSource} alt="" style={chatbotStyles.providerOptionLogo} />
      ) : (
        <span style={chatbotStyles.providerOptionInitial}>
          {getProviderInitial(label, providerId)}
        </span>
      )}
    </span>
  );
};

/**
 * Header renders the top section of the chatbot panel, including the title and
 * a button to clear the current conversation. It receives a callback to handle
 * message clearing, typically triggered by user interaction.
 */
export const Header = ({
  currentSessionId,
  clearMessages,
  openSideBar,
  messages,
  providers = [],
  selectedProviderId = "local",
  onProviderChange,
}: HeaderProps) => {
  const [showExportMenu, setShowExportMenu] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement | null>(null);
  const providerMenuRef = useRef<HTMLDivElement | null>(null);
  const [showProviderMenu, setShowProviderMenu] = useState(false);

  const selectedProvider =
    providers.find((provider) => provider.id === selectedProviderId) ||
    providers[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        showExportMenu &&
        exportMenuRef.current &&
        !exportMenuRef.current.contains(event.target as Node)
      ) {
        setShowExportMenu(false);
      }

      if (
        showProviderMenu &&
        providerMenuRef.current &&
        !providerMenuRef.current.contains(event.target as Node)
      ) {
        setShowProviderMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showExportMenu, showProviderMenu]);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowProviderMenu(false);
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  const selectProvider = (providerId: string) => {
    onProviderChange?.(providerId);
    setShowProviderMenu(false);
  };

  const focusProviderOption = (direction: 1 | -1) => {
    const options = Array.from(
      providerMenuRef.current?.querySelectorAll<HTMLButtonElement>(
        '[role="option"]:not([aria-disabled="true"])',
      ) || [],
    );
    if (options.length === 0) return;

    const currentIndex = options.indexOf(
      document.activeElement as HTMLButtonElement,
    );
    const nextIndex =
      currentIndex < 0
        ? direction === 1
          ? 0
          : options.length - 1
        : (currentIndex + direction + options.length) % options.length;
    options[nextIndex].focus();
  };

  const handleProviderControlKeyDown = (event: ReactKeyboardEvent) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    setShowProviderMenu(true);
    window.setTimeout(() => {
      focusProviderOption(event.key === "ArrowDown" ? 1 : -1);
    }, 0);
  };

  const handleProviderMenuKeyDown = (event: ReactKeyboardEvent) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      focusProviderOption(event.key === "ArrowDown" ? 1 : -1);
    }
    if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      const direction = event.key === "Home" ? 1 : -1;
      const options = Array.from(
        providerMenuRef.current?.querySelectorAll<HTMLButtonElement>(
          '[role="option"]:not([aria-disabled="true"])',
        ) || [],
      );
      options[direction === 1 ? 0 : options.length - 1]?.focus();
    }
  };

  return (
    <div style={chatbotStyles.chatbotHeader}>
      <button
        onClick={openSideBar}
        style={chatbotStyles.openSidebarButton}
        aria-label="Toggle sidebar"
      >
        {getChatbotText("sidebarLabel")}
      </button>
      {providers.length > 0 && (
        <div
          ref={providerMenuRef}
          className="chatbot-provider-selector"
          style={chatbotStyles.providerSelector}
        >
          <button
            type="button"
            aria-haspopup="listbox"
            aria-expanded={showProviderMenu}
            aria-label="Select model provider"
            aria-controls="chatbot-provider-menu"
            className="chatbot-provider-control"
            style={chatbotStyles.providerControl}
            onClick={() => setShowProviderMenu((previous) => !previous)}
            onKeyDown={handleProviderControlKeyDown}
          >
            <span style={chatbotStyles.providerControlText}>
              <span style={chatbotStyles.providerControlLabel}>
                {selectedProvider?.label || "Choose a provider"}
              </span>
              <span style={chatbotStyles.providerControlModel}>
                {selectedProvider?.model || "No provider selected"}
              </span>
            </span>
            <ChevronDown
              size={16}
              aria-hidden="true"
              style={showProviderMenu ? { transform: "rotate(180deg)" } : {}}
            />
          </button>
          {showProviderMenu && (
            <div
              id="chatbot-provider-menu"
              role="listbox"
              aria-label="Available model providers"
              className="chatbot-provider-menu"
              style={chatbotStyles.providerMenu}
              onKeyDown={handleProviderMenuKeyDown}
            >
              {providers.map((provider) => {
                const isDisabled =
                  provider.id !== "local" && !provider.configured;
                const isSelected = provider.id === selectedProvider?.id;

                return (
                  <button
                    key={provider.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    aria-disabled={isDisabled}
                    aria-label={
                      isDisabled
                        ? `${provider.label}, API key not configured`
                        : provider.label
                    }
                    className={`chatbot-provider-option${
                      isSelected ? " is-selected" : ""
                    }${isDisabled ? " is-unavailable" : ""}`}
                    style={{
                      ...chatbotStyles.providerOption,
                      ...(isSelected
                        ? chatbotStyles.providerOptionSelected
                        : {}),
                      ...(isDisabled
                        ? chatbotStyles.providerOptionDisabled
                        : {}),
                    }}
                    onClick={() => {
                      if (!isDisabled) {
                        selectProvider(provider.id);
                      }
                    }}
                  >
                    <ProviderIcon
                      providerId={provider.id}
                      label={provider.label}
                    />
                    <span style={chatbotStyles.providerOptionText}>
                      <span style={chatbotStyles.providerOptionLabel}>
                        {provider.label}
                      </span>
                      <span
                        className="chatbot-provider-option-model"
                        style={chatbotStyles.providerOptionModel}
                      >
                        {provider.model}
                      </span>
                    </span>
                    <span
                      className="chatbot-provider-option-status"
                      style={chatbotStyles.providerOptionStatus}
                    >
                      {isSelected && <Check size={15} aria-hidden="true" />}
                      {isDisabled && (
                        <span
                          className="chatbot-provider-warning"
                          role="img"
                          aria-label="API key not configured"
                          data-tooltip="API key not configured"
                        >
                          <TriangleAlert size={14} aria-hidden="true" />
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
      {currentSessionId !== null && (
        <div ref={exportMenuRef} style={chatbotStyles.headerActions}>
          <div style={{ position: "relative", display: "inline-block" }}>
            {/* Export button */}
            <button
              onClick={() => setShowExportMenu((prev) => !prev)}
              style={chatbotStyles.exportButton}
              title="Export chat"
              aria-label="Export chat"
            >
              <Upload size={16} />
            </button>

            {/* Export menu */}
            {showExportMenu && (
              <div style={chatbotStyles.exportMenu}>
                <button
                  style={chatbotStyles.exportMenuItem}
                  onClick={() => {
                    exportAsTxt(messages);
                    setShowExportMenu(false);
                  }}
                >
                  <FileText size={20} />
                  <span>.txt</span>
                </button>
                <button
                  style={chatbotStyles.exportMenuItem}
                  onClick={() => {
                    exportAsMd(messages);
                    setShowExportMenu(false);
                  }}
                >
                  <FileCode size={20} />
                  <span>.md</span>
                </button>
                <button
                  style={chatbotStyles.exportMenuItem}
                  onClick={() => {
                    exportAsDocx(messages);
                    setShowExportMenu(false);
                  }}
                >
                  <FileSpreadsheet size={20} />
                  <span>.docx</span>
                </button>
                <button
                  style={chatbotStyles.exportMenuItem}
                  onClick={() => {
                    exportAsPdf(messages);
                    setShowExportMenu(false);
                  }}
                >
                  <File size={20} />
                  <span>.pdf</span>
                </button>
              </div>
            )}
          </div>

          <button
            onClick={() => clearMessages(currentSessionId)}
            style={chatbotStyles.clearButton}
            title="Clear chat"
            aria-label="Clear chat"
          >
            <Trash2 size={16} />
          </button>
        </div>
      )}
    </div>
  );
};
