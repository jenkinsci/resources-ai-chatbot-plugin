package io.jenkins.plugins.chatbot;

import hudson.Extension;
import hudson.model.RootAction;
import hudson.model.User;
import jakarta.servlet.ServletException;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import jenkins.model.Jenkins;
import net.sf.json.JSONObject;
import org.apache.commons.io.IOUtils;
import org.kohsuke.stapler.StaplerRequest2;
import org.kohsuke.stapler.StaplerResponse2;
import org.kohsuke.stapler.verb.GET;

@Extension
public class ChatbotRootAction implements RootAction {

    // Ensure this matches your Python config prefix
    private static final String PYTHON_BACKEND_URL = "http://localhost:8000/api/chatbot";

    @Override
    public String getIconFileName() {
        return null;
    }

    @Override
    public String getDisplayName() {
        return null;
    }

    @Override
    public String getUrlName() {
        return "chatbot";
    }

    /**
     * CENTRAL ROUTING METHOD
     * Handles ALL requests to /chatbot/... to prevent routing conflicts.
     */
    public void doDynamic(StaplerRequest2 req, StaplerResponse2 rsp) throws IOException, ServletException {
        // 1. Security Check
        checkPermissions();

        // 2. Normalize Path
        String path = req.getRestOfPath();
        if (path.startsWith("/")) {
            path = path.substring(1);
        }

        // Prevent directory traversal attacks
        if (path.contains("..")) {
            rsp.sendError(400, "Invalid path");
            return;
        }

        // 3. Routing Logic
        // STRICT CHECK: Only if path is EXACTLY "sessions" or "sessions/" do we create a new session.
        StringBuilder targetUrlBuilder = new StringBuilder(PYTHON_BACKEND_URL);
        targetUrlBuilder.append("/").append(path);

        if (req.getQueryString() != null) {
            targetUrlBuilder.append("?").append(req.getQueryString());
        }

        // EVERYTHING ELSE (messages, file uploads, etc.) -> Proxy directly to Python
        String targetUrl = targetUrlBuilder.toString();

        String method = req.getMethod();
        if ("POST".equalsIgnoreCase(method)) {
            proxyStreamRequest(req, rsp, targetUrl);
        } else if ("GET".equalsIgnoreCase(method)) {
            proxyGetRequest(rsp, targetUrl);
        } else if ("DELETE".equalsIgnoreCase(method)) {
            proxyDeleteRequest(rsp, targetUrl);
        } else {
            rsp.sendError(405, "Method Not Allowed");
        }
    }

    /**
     * DEBUG ENDPOINT: /chatbot/whoAmI
     */
    @GET
    public void doWhoAmI(StaplerRequest2 req, StaplerResponse2 rsp) throws IOException, ServletException {
        User user = User.current();
        String userId = (user != null) ? user.getId() : "anonymous";
        String fullName = (user != null) ? user.getFullName() : "N/A";
        boolean isAdmin = Jenkins.get().hasPermission(Jenkins.ADMINISTER);

        JSONObject json = new JSONObject();
        json.put("user_id", userId);
        json.put("full_name", fullName);
        json.put("is_admin", isAdmin);
        json.put("jenkins_url", Jenkins.get().getRootUrl());

        rsp.setContentType("application/json");
        rsp.getWriter().write(json.toString());
    }

    // ========================================================================
    // HELPERS
    // ========================================================================

    private void checkPermissions() {
        Jenkins.get().checkPermission(Jenkins.READ);
    }

    private void addAuthHeaders(HttpURLConnection conn) {
        User user = User.current();
        if (user != null) {
            // Identity Injection
            conn.setRequestProperty("X-Jenkins-User-ID", user.getId());
            // Use URL encoder for names to handle special characters/spaces safely
            String cleanName = user.getDisplayName().replaceAll("[^a-zA-Z0-9 ]", "");
            conn.setRequestProperty("X-Jenkins-User-Name", cleanName);
        } else {
            conn.setRequestProperty("X-Jenkins-User-ID", "anonymous");
            conn.setRequestProperty("X-Jenkins-User-Name", "Anonymous");
        }
    }

    private void proxyStreamRequest(StaplerRequest2 req, StaplerResponse2 rsp, String targetUrl) throws IOException {
        HttpURLConnection conn = null;
        try {
            java.net.URL url = java.net.URI.create(targetUrl).toURL();
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod(req.getMethod());
            conn.setRequestProperty("Content-Type", req.getContentType());
            addAuthHeaders(conn);
            conn.setDoOutput(true);

            IOUtils.copy(req.getInputStream(), conn.getOutputStream());
            copyBackendResponse(conn, rsp);
        } catch (Exception e) {
            handleProxyError(rsp, e);
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    private void proxyGetRequest(StaplerResponse2 rsp, String targetUrl) throws IOException {
        HttpURLConnection conn = null;
        try {
            java.net.URL url = java.net.URI.create(targetUrl).toURL();
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            addAuthHeaders(conn);
            copyBackendResponse(conn, rsp);
        } catch (Exception e) {
            handleProxyError(rsp, e);
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    private void proxyDeleteRequest(StaplerResponse2 rsp, String targetUrl) throws IOException {
        HttpURLConnection conn = null;
        try {
            java.net.URL url = java.net.URI.create(targetUrl).toURL();
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("DELETE");
            addAuthHeaders(conn);
            copyBackendResponse(conn, rsp);
        } catch (Exception e) {
            handleProxyError(rsp, e);
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    private void copyBackendResponse(HttpURLConnection conn, StaplerResponse2 rsp) throws IOException {
        int status = conn.getResponseCode();
        rsp.setStatus(status);
        rsp.setContentType(conn.getContentType());

        InputStream backendStream = (status >= 400) ? conn.getErrorStream() : conn.getInputStream();
        if (backendStream != null) {
            IOUtils.copy(backendStream, rsp.getOutputStream());
        }
    }

    private void handleProxyError(StaplerResponse2 rsp, Exception e) throws IOException {
        e.printStackTrace();
        rsp.sendError(500, "Chatbot Proxy Error: " + e.getMessage());
    }
}
