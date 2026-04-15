package io.jenkins.plugins.chatbot;

import static org.junit.Assert.assertTrue;

import java.io.File;
import org.junit.Test;

/**
 * Canary test to verify filesystem stability in virtualized environments (WSL2/9P).
 */
public class EnvironmentStabilityTest {
    @Test
    public void testFileSystemAccess() {
        File workspace = new File(".");
        assertTrue("Workspace should be readable by the JVM", workspace.canRead());
    }
}
