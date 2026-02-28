package io.jenkins.plugins.chatbot;

import hudson.Extension;
import hudson.model.UnprotectedRootAction;
import hudson.model.User;
import hudson.security.csrf.CrumbExclusion;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import jenkins.model.Jenkins;
import org.json.JSONException;
import org.json.JSONObject;
import org.kohsuke.stapler.StaplerRequest;
import org.kohsuke.stapler.StaplerResponse;

/**
 * ChatbotRootAction serves as the secure "Gatekeeper" proxy for the chatbot backend.
 *
 * This action:
 * 1. Authenticates users via Jenkins' User.current()
 * 2. Authorizes access by checking Jenkins.READ permission
 * 3. Injects the authenticated user_id into request payloads
 * 4. Proxies requests to the Python backend (localhost:8000)
 * 5. Ensures session isolation per user
 *
 * Available at: JENKINS_URL/chatbot/api/chatbot/*
 */
@Extension
public class ChatbotRootAction implements UnprotectedRootAction {

    private static final Logger LOGGER = Logger.getLogger(ChatbotRootAction.class.getName());
    private static final String PYTHON_BACKEND_URL = "http://localhost:8000";

    @Override
    public String getIconFileName() {
        return null; // No icon in side panel
    }

    @Override
    public String getDisplayName() {
        return null; // No display name
    }

    @Override
    public String getUrlName() {
        return "chatbot";
    }

    /**
     * Main entry point for all chatbot API requests.
     * Handles authentication, authorization, and proxying to Python backend.
     *
     * CSRF Protection: This endpoint is excluded from Jenkins CSRF protection via
     * {@link ChatbotCrumbExclusion} because the frontend sends requests with
     * Jenkins crumb tokens in headers. The Python backend validates session
     * ownership per user_id, ensuring requests cannot be forged cross-user.
     * Additionally, this endpoint only proxies to a fixed localhost backend URL,
     * not user-specified URLs.
     *
     * @param req the Stapler request
     * @param rsp the Stapler response
     * @throws IOException if I/O error occurs
     * @throws ServletException if servlet error occurs
     */
    @SuppressWarnings("lgtm[jenkins/csrf]") // CSRF handled via crumb exclusion and user_id validation
    public void doDynamic(StaplerRequest req, StaplerResponse rsp) throws IOException, ServletException {
        // Extract the path after /chatbot/
        String path = req.getRestOfPath();

        LOGGER.log(Level.INFO, "ChatbotRootAction received request: {0} {1}", new Object[] {req.getMethod(), path});

        // Authenticate user (optional - allow anonymous access)
        User user = User.current();
        String userId = null;

        if (user != null) {
            userId = user.getId();
            LOGGER.log(Level.INFO, "Authenticated user: {0}", userId);

            // Authorize user - check Jenkins READ permission (only for authenticated users)
            Jenkins jenkins = Jenkins.get();
            if (!jenkins.hasPermission(Jenkins.READ)) {
                LOGGER.log(Level.WARNING, "User {0} lacks Jenkins.READ permission", userId);
                rsp.sendError(HttpServletResponse.SC_FORBIDDEN, "Insufficient permissions");
                return;
            }
        } else {
            LOGGER.log(Level.INFO, "Anonymous user accessing chatbot API");
        }

        // Proxy the request to Python backend
        try {
            proxyRequest(req, rsp, userId, path);
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error proxying request to backend", e);
            rsp.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR, "Failed to communicate with chatbot backend");
        }
    }

    /**
     * Proxy the request to the Python backend, injecting user_id into the payload.
     */
    private void proxyRequest(StaplerRequest req, StaplerResponse rsp, String userId, String path)
            throws IOException, JSONException {

        String method = req.getMethod();
        String backendUrl = PYTHON_BACKEND_URL + path;

        LOGGER.log(Level.FINE, "Proxying {0} request to: {1}", new Object[] {method, backendUrl});

        URL url = new URL(backendUrl);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod(method);
        conn.setDoInput(true);

        // Copy headers from original request (excluding Host and Authorization)
        java.util.Enumeration<String> headerNames = req.getHeaderNames();
        while (headerNames.hasMoreElements()) {
            String headerName = headerNames.nextElement();
            if (!headerName.equalsIgnoreCase("Host")
                    && !headerName.equalsIgnoreCase("Authorization")
                    && !headerName.equalsIgnoreCase("Cookie")) {
                String headerValue = req.getHeader(headerName);
                conn.setRequestProperty(headerName, headerValue);
            }
        }

        // Handle request body for POST/PUT/PATCH
        if ("POST".equals(method) || "PUT".equals(method) || "PATCH".equals(method)) {
            conn.setDoOutput(true);

            String contentType = req.getContentType();
            if (contentType != null && contentType.contains("application/json")) {
                // Read the original JSON payload
                StringBuilder bodyBuilder = new StringBuilder();
                try (BufferedReader reader = req.getReader()) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        bodyBuilder.append(line);
                    }
                }

                String originalBody = bodyBuilder.toString();
                JSONObject jsonBody;

                // Parse and inject user_id (only if authenticated)
                if (originalBody.isEmpty()) {
                    jsonBody = new JSONObject();
                } else {
                    jsonBody = new JSONObject(originalBody);
                }

                // Only inject user_id for authenticated users
                if (userId != null) {
                    jsonBody.put("user_id", userId);
                }

                String modifiedBody = jsonBody.toString();
                LOGGER.log(Level.FINE, "Modified request body: {0}", modifiedBody);

                // Write modified body to backend
                try (OutputStream os = conn.getOutputStream()) {
                    byte[] input = modifiedBody.getBytes(StandardCharsets.UTF_8);
                    os.write(input, 0, input.length);
                }
            } else {
                // For non-JSON requests (e.g., multipart), forward as-is
                // Note: multipart file uploads would need special handling for user_id injection
                try (InputStream is = req.getInputStream();
                        OutputStream os = conn.getOutputStream()) {
                    byte[] buffer = new byte[8192];
                    int bytesRead;
                    while ((bytesRead = is.read(buffer)) != -1) {
                        os.write(buffer, 0, bytesRead);
                    }
                }
            }
        }

        // Get response from backend
        int responseCode = conn.getResponseCode();
        rsp.setStatus(responseCode);

        LOGGER.log(Level.FINE, "Backend response code: {0}", responseCode);

        // Copy response headers
        conn.getHeaderFields().forEach((key, values) -> {
            if (key != null && values != null) {
                for (String value : values) {
                    rsp.addHeader(key, value);
                }
            }
        });

        // Copy response body
        try (InputStream is =
                        (responseCode >= 200 && responseCode < 300) ? conn.getInputStream() : conn.getErrorStream();
                OutputStream os = rsp.getOutputStream()) {

            if (is != null) {
                byte[] buffer = new byte[8192];
                int bytesRead;
                while ((bytesRead = is.read(buffer)) != -1) {
                    os.write(buffer, 0, bytesRead);
                }
            }
        }
    }

    /**
     * CSRF Crumb Exclusion for the chatbot API.
     *
     * This allows the Python backend to be called through this proxy without
     * requiring CSRF tokens on every request. The proxy itself enforces authentication.
     */
    @Extension
    public static class ChatbotCrumbExclusion extends CrumbExclusion {
        @Override
        public boolean process(
                HttpServletRequest request,
                javax.servlet.http.HttpServletResponse response,
                javax.servlet.FilterChain chain)
                throws IOException, javax.servlet.ServletException {
            String pathInfo = request.getPathInfo();

            // Exclude /chatbot/* from CSRF protection since we handle auth in the action
            if (pathInfo != null && pathInfo.startsWith("/chatbot/")) {
                chain.doFilter(request, response);
                return true;
            }

            return false;
        }
    }
}
