package io.jenkins.plugins.chatbot;

import static io.jenkins.plugins.chatbot.BackendConfigurationTest.save;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.sun.net.httpserver.HttpServer;
import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.function.Supplier;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.DisabledOnOs;
import org.junit.jupiter.api.condition.OS;
import org.junit.jupiter.api.io.TempDir;
import org.jvnet.hudson.test.JenkinsRule;
import org.jvnet.hudson.test.junit.jupiter.WithJenkins;

@WithJenkins
class BackendProcessTest {

    @Test
    void acceptsPreparedBackendDirectory(@TempDir File directory) throws IOException {
        createBackendDirectory(directory);

        assertNull(BackendProcess.validateDirectory(directory.getPath()));
    }

    @Test
    void acceptsWindowsVirtualEnvironment(@TempDir File directory) throws IOException {
        writeFile(new File(directory, "api/main.py"), "");
        writeFile(new File(directory, "venv/Scripts/python.exe"), "");

        assertNull(BackendProcess.validateDirectory(directory.getPath()));
    }

    @Test
    void rejectsDirectoryThatIsNotChatbotCore(@TempDir File directory) {
        assertTrue(BackendProcess.validateDirectory(directory.getPath()).contains("api/main.py"));
    }

    @Test
    void rejectsDirectoryWithoutVirtualEnvironment(@TempDir File directory) throws IOException {
        writeFile(new File(directory, "api/main.py"), "");

        assertTrue(BackendProcess.validateDirectory(directory.getPath()).contains("make setup-backend"));
    }

    @Test
    void detectsRunningChatbotBackend() throws IOException {
        HttpServer server = startServer("{\"status\":\"healthy\",\"llm_available\":false}");
        try {
            assertEquals(BackendProcess.Health.RUNNING, BackendProcess.checkHealth(urlOf(server)));
        } finally {
            server.stop(0);
        }
    }

    @Test
    void detectsOtherServiceOnThePort() throws IOException {
        HttpServer server = startServer("<html>Some other app</html>");
        try {
            assertEquals(BackendProcess.Health.OTHER_SERVICE, BackendProcess.checkHealth(urlOf(server)));
        } finally {
            server.stop(0);
        }
    }

    @Test
    void detectsWhenNothingIsRunning() throws IOException {
        assertEquals(BackendProcess.Health.NOT_RUNNING, BackendProcess.checkHealth(freeUrl()));
    }

    @Test
    @DisabledOnOs(OS.WINDOWS)
    void restartsWhenDirectoryChanges(JenkinsRule jenkins, @TempDir File first, @TempDir File second) throws Exception {
        createFakeBackend(first, "exec sleep 60");
        createFakeBackend(second, "exec sleep 60");
        String url = freeUrl();

        save(url, true, first.getPath());
        Process original = waitFor(() -> BackendProcess.get().getProcess());

        save(url, true, second.getPath());
        Process restarted = waitFor(() -> {
            Process current = BackendProcess.get().getProcess();
            return current != original ? current : null;
        });

        assertFalse(original.isAlive());
        assertTrue(restarted.isAlive());
    }

    @Test
    @DisabledOnOs(OS.WINDOWS)
    void keepsRunningWhenSettingsAreUnchanged(JenkinsRule jenkins, @TempDir File directory) throws Exception {
        createFakeBackend(directory, "exec sleep 60");
        String url = freeUrl();

        save(url, true, directory.getPath());
        Process original = waitFor(() -> BackendProcess.get().getProcess());

        save(url, true, directory.getPath());

        assertSame(original, BackendProcess.get().getProcess());
        assertTrue(original.isAlive());
    }

    @Test
    @DisabledOnOs(OS.WINDOWS)
    void stopsWhenAutoStartIsDisabled(JenkinsRule jenkins, @TempDir File directory) throws Exception {
        createFakeBackend(directory, "exec sleep 60");
        String url = freeUrl();

        save(url, true, directory.getPath());
        Process original = waitFor(() -> BackendProcess.get().getProcess());

        save(url, false, directory.getPath());

        assertFalse(original.isAlive());
        assertNull(BackendProcess.get().getProcess());
    }

    @Test
    @DisabledOnOs(OS.WINDOWS)
    void reportsWhenBackendExits(JenkinsRule jenkins, @TempDir File directory) throws Exception {
        createFakeBackend(directory, "exit 3");

        save(freeUrl(), true, directory.getPath());
        String problem = waitFor(() -> BackendProcess.get().getProblem());

        assertTrue(problem.contains("exit code 3"), problem);
        assertTrue(BackendProcess.get().isActivated());
    }

    @Test
    @DisabledOnOs(OS.WINDOWS)
    void startsAgainAfterExitWhenSaved(JenkinsRule jenkins, @TempDir File directory) throws Exception {
        createFakeBackend(directory, "exit 3");
        String url = freeUrl();

        save(url, true, directory.getPath());
        Process crashed = waitFor(() -> BackendProcess.get().getProcess());
        waitFor(() -> BackendProcess.get().getProblem());

        createFakeBackend(directory, "exec sleep 60");
        save(url, true, directory.getPath());
        Process restarted = waitFor(() -> {
            Process current = BackendProcess.get().getProcess();
            return current != crashed && current != null && current.isAlive() ? current : null;
        });

        assertNotSame(crashed, restarted);
        assertNull(BackendProcess.get().getProblem());
    }

    static void createBackendDirectory(File directory) throws IOException {
        writeFile(new File(directory, "api/main.py"), "");
        writeFile(new File(directory, "venv/bin/python"), "");
    }

    private static void createFakeBackend(File directory, String command) throws IOException {
        createBackendDirectory(directory);
        File python = new File(directory, "venv/bin/python");
        writeFile(python, "#!/bin/sh\n" + command + "\n");
        assertTrue(python.setExecutable(true));
    }

    private static void writeFile(File file, String content) throws IOException {
        Files.createDirectories(file.getParentFile().toPath());
        Files.writeString(file.toPath(), content, StandardCharsets.UTF_8);
    }

    private static String freeUrl() throws IOException {
        try (ServerSocket socket = new ServerSocket(0)) {
            return "http://localhost:" + socket.getLocalPort();
        }
    }

    private static <T> T waitFor(Supplier<T> supplier) throws InterruptedException {
        for (int attempt = 0; attempt < 200; attempt++) {
            T value = supplier.get();
            if (value != null) {
                return value;
            }
            Thread.sleep(50);
        }
        throw new AssertionError("Timed out waiting for the backend");
    }

    private static HttpServer startServer(String healthResponse) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/health", exchange -> {
            byte[] body = healthResponse.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            try (OutputStream output = exchange.getResponseBody()) {
                output.write(body);
            }
        });
        server.start();
        return server;
    }

    private static String urlOf(HttpServer server) {
        return "http://localhost:" + server.getAddress().getPort();
    }
}
