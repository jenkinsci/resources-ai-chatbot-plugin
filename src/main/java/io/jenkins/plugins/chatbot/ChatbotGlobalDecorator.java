package io.jenkins.plugins.chatbot;

import hudson.Extension;
import hudson.model.PageDecorator;

@Extension
public class ChatbotGlobalDecorator extends PageDecorator {
    /**
     * Returns the configured FastAPI backend URL for the Jelly view.
     *
     * @return the configured backend URL
     */
    public String getBackendUrl() {
        return BackendConfiguration.get().getBackendUrl();
    }
}
