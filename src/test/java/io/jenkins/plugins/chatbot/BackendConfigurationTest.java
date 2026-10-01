package io.jenkins.plugins.chatbot;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;
import org.jvnet.hudson.test.JenkinsRule;
import org.jvnet.hudson.test.junit.jupiter.WithJenkins;

@WithJenkins
class BackendConfigurationTest {

    @Test
    void usesLocalhostAsTheDefaultBackendUrl(JenkinsRule jenkins) {
        BackendConfiguration configuration = new BackendConfiguration();

        assertEquals("http://localhost:8000", configuration.getBackendUrl());
    }
}
