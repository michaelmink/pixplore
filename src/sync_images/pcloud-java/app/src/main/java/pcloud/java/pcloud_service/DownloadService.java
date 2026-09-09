package pcloud.java.pcloud_service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import com.github.sardine.Sardine;
import com.github.sardine.SardineFactory;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.stream.Collectors;


@Service
public class DownloadService {

    // values from config
    @Value("${pcloud.api.username}")
    private String username;
    @Value("${pcloud.api.password}")
    private String password;


    public void downloadFile(String path, String downloadPath) throws IOException {
        System.out.println("Downloading File: " + path + " to " + downloadPath);

        Sardine sardine = SardineFactory.begin(username, password);

        // Zielverzeichnis erstellen falls nicht vorhanden
        Path targetDir = Paths.get(downloadPath);
        Files.createDirectories(targetDir);

        // Dateiname aus dem Pfad extrahieren
        String decodedPath = URLDecoder.decode(path, StandardCharsets.UTF_8);
        String fileName = decodedPath.substring(decodedPath.lastIndexOf('/') + 1);
        Path targetFile = targetDir.resolve(fileName);
        String encodedPath = Arrays.stream(decodedPath.split("/", -1))
            .map(segment -> URLEncoder.encode(segment, StandardCharsets.UTF_8)
                .replace("+", "%20"))
            .collect(Collectors.joining("/"));

        // Datei herunterladen und lokal speichern
        try (InputStream in = sardine.get("https://ewebdav.pcloud.com" + encodedPath)) {
            Files.copy(in, targetFile, StandardCopyOption.REPLACE_EXISTING);
        }

        System.out.println("Downloaded: " + targetFile.toAbsolutePath());
    }

}
