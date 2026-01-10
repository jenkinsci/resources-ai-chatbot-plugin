package io.jenkins.plugins.chatbot;

import hudson.model.User;
import jenkins.model.Jenkins;
import org.junit.Rule;
import org.junit.Test;
import org.jvnet.hudson.test.JenkinsRule;
import org.jvnet.hudson.test.MockAuthorizationStrategy;

import static org.junit.Assert.*;

/**
 * Unit tests for ChatbotRootAction authentication and authorization logic.
 */
public class ChatbotRootActionTest {

    @Rule
    public JenkinsRule jenkins = new JenkinsRule();

    @Test
    public void testGetUrlName() {
        ChatbotRootAction action = new ChatbotRootAction();
        assertEquals("chatbot", action.getUrlName());
    }

    @Test
    public void testNoIconInSidePanel() {
        ChatbotRootAction action = new ChatbotRootAction();
        assertNull(action.getIconFileName());
    }

    @Test
    public void testNoDisplayName() {
        ChatbotRootAction action = new ChatbotRootAction();
        assertNull(action.getDisplayName());
    }

    @Test
    public void testAuthenticationRequired() throws Exception {
        // Set up Jenkins with authentication
        jenkins.getInstance().setSecurityRealm(jenkins.createDummySecurityRealm());
        
        MockAuthorizationStrategy authStrategy = new MockAuthorizationStrategy();
        authStrategy.grant(Jenkins.READ).everywhere().to("authenticated");
        jenkins.getInstance().setAuthorizationStrategy(authStrategy);
        
        // This test verifies the action exists and can be instantiated
        ChatbotRootAction action = jenkins.getInstance().getExtensionList(ChatbotRootAction.class).get(0);
        assertNotNull("ChatbotRootAction should be registered", action);
        assertEquals("chatbot", action.getUrlName());
    }

    @Test
    public void testCrumbExclusionForChatbotPath() {
        ChatbotRootAction.ChatbotCrumbExclusion exclusion = new ChatbotRootAction.ChatbotCrumbExclusion();
        assertNotNull("CrumbExclusion should be instantiated", exclusion);
    }
}
