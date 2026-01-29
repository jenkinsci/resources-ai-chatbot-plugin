package io.jenkins.plugins.chatbot;

import hudson.Extension;
import hudson.model.PageDecorator;
import hudson.model.User;

@Extension
public class ChatbotGlobalDecorator extends PageDecorator {
    public ChatbotGlobalDecorator() {
        super();
    }

    public String getCurrentUserId() {
        User user = User.current();
        return (user != null) ? user.getId() : "anonymous";
    }

    public String getCurrentUserDisplayName() {
        User user = User.current();
        return (user != null) ? user.getDisplayName() : "User";
    }
}
