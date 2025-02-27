import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import org.wso2.balana.Balana;
import org.wso2.balana.PDP;
import org.wso2.balana.PDPConfig;
import org.wso2.balana.finder.PolicyFinder;
import org.wso2.balana.finder.PolicyFinderModule;
import org.wso2.balana.finder.impl.FileBasedPolicyFinderModule;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class SimplePDPServer {
    private static PDP pdp;

    public static void main(String[] args) throws Exception {
        // Initialize Balana PDP
        initializePDP();

        // Create HTTP server
        HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);
        server.createContext("/pdp", new PDPHandler());
        server.setExecutor(null);
        server.start();
        
        System.out.println("PDP Server started on port 8080");
        System.out.println("Send XACML requests to http://localhost:8080/pdp");
    }

    private static void initializePDP() {
        // Use file based policy finder
        PolicyFinderModule policyFinderModule = new FileBasedPolicyFinderModule();
        PolicyFinder policyFinder = new PolicyFinder();
        List<PolicyFinderModule> policyModules = new ArrayList<>();
        policyModules.add(policyFinderModule);
        policyFinder.setModules(policyModules);

        // Create PDP config with policy finder
        PDPConfig pdpConfig = new PDPConfig(null, policyFinder, null);
        
        // Create new PDP instance
        pdp = new PDP(pdpConfig);
        
        System.out.println("Balana PDP initialized");
    }

    static class PDPHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            // Only handle POST requests
            if ("POST".equals(exchange.getRequestMethod())) {
                // Read request
                InputStream requestBody = exchange.getRequestBody();
                byte[] requestBytes = requestBody.readAllBytes();
                String xacmlRequest = new String(requestBytes, StandardCharsets.UTF_8);

                // Evaluate XACML request
                String xacmlResponse = pdp.evaluate(xacmlRequest);

                // Send response
                exchange.getResponseHeaders().set("Content-Type", "application/xml");
                exchange.sendResponseHeaders(200, xacmlResponse.length());
                OutputStream os = exchange.getResponseBody();
                os.write(xacmlResponse.getBytes());
                os.close();
            } else {
                // Method not allowed
                exchange.sendResponseHeaders(405, 0);
                exchange.getResponseBody().close();
            }
        }
    }
}