package io.jenkins.plugins.chatbot;

import hudson.Extension;
import hudson.model.PageDecorator;

@Extension
public class ChatbotGlobalDecorator extends PageDecorator {
    public ChatbotGlobalDecorator() {
        super(ChatbotGlobalDecorator.class);
    }
}
