package io.jenkins.plugins.chatbot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;

import hudson.model.Descriptor;
import java.io.File;
import java.io.IOException;
import net.sf.json.JSONObject;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.jvnet.hudson.test.JenkinsRule;
import org.jvnet.hudson.test.junit.jupiter.WithJenkins;
import org.kohsuke.stapler.StaplerRequest2;

@WithJenkins
class BackendConfigurationTest {

    @Test
    void usesLocalhostAsTheDefaultBackendUrl(JenkinsRule jenkins) {
        BackendConfiguration configuration = new BackendConfiguration();

        assertEquals("http://localhost:8000", configuration.getBackendUrl());
    }

    @Test
    void savesSettingsWhenAutoStartIsDisabled(JenkinsRule jenkins) throws Exception {
        BackendConfiguration configuration = BackendConfiguration.get();

        save("http://localhost:9000/", false, "/opt/chatbot-core");

        assertEquals("http://localhost:9000", configuration.getBackendUrl());
        assertFalse(configuration.isAutoStartBackend());
        assertEquals("/opt/chatbot-core", configuration.getBackendDirectory());
    }

    @Test
    void rejectsAutoStartWithoutBackendDirectory(JenkinsRule jenkins) {
        Descriptor.FormException exception =
                assertThrows(Descriptor.FormException.class, () -> save("http://localhost:8000", true, ""));

        assertEquals("backendDirectory", exception.getFormField());
    }

    @Test
    void rejectsAutoStartForRemoteBackendUrl(JenkinsRule jenkins, @TempDir File directory) throws IOException {
        BackendProcessTest.createBackendDirectory(directory);

        Descriptor.FormException exception = assertThrows(
                Descriptor.FormException.class, () -> save("https://chatbot.example.com", true, directory.getPath()));

        assertEquals("backendUrl", exception.getFormField());
    }

    @Test
    void rejectsAutoStartForBackendUrlWithoutPort(JenkinsRule jenkins, @TempDir File directory) throws IOException {
        BackendProcessTest.createBackendDirectory(directory);

        Descriptor.FormException exception =
                assertThrows(Descriptor.FormException.class, () -> save("http://localhost", true, directory.getPath()));

        assertEquals("backendUrl", exception.getFormField());
    }

    static void save(String backendUrl, boolean autoStart, String directory) throws Descriptor.FormException {
        JSONObject json = new JSONObject()
                .element("backendUrl", backendUrl)
                .element("autoStartBackend", autoStart)
                .element("backendDirectory", directory);
        BackendConfiguration.get().configure((StaplerRequest2) null, json);
    }
}
