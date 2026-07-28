
package pcloud.java.chroma_service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Map;

@Service
public class ChromaService {
    
    private final RestClient restClient;
    private String collectionId = "pixplore";
    
    public ChromaService() {
        this.restClient = RestClient.builder()
            .baseUrl("http://localhost:8000/api/v2")
            .build();
    }

    // File existence check
    public boolean checkFileExists(String fileName) {
        var response = restClient.get()
            .uri("/collections/{collectionId}/files/{fileName}", collectionId, fileName)
            .retrieve()
            .body(Map.class);
        System.out.println("http://localhost:8000/api/v2/collections/" + collectionId + "/files/" + fileName);
        return response != null && response.containsKey("exists") && (Boolean) response.get("exists");
    }
}