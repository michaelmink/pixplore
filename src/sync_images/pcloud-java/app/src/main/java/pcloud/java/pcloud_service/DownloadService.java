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


@Service
public class DownloadService {

    // values from config
    @Value("${pcloud.api.username}")
    private String username;
    @Value("${pcloud.api.password}")
    private String password;
    @Value("${pcloud.download.path}")
    private String downloadPath;

    public void downloadFile(String path) throws IOException {
        System.out.println("Downloading File: " + path + " to " + downloadPath);

        Sardine sardine = SardineFactory.begin(username, password);

        // Zielverzeichnis erstellen falls nicht vorhanden
        Path targetDir = Paths.get(downloadPath);
        Files.createDirectories(targetDir);

        // Dateiname aus dem Pfad extrahieren
        String fileName = path.substring(path.lastIndexOf('/') + 1);
        Path targetFile = targetDir.resolve(fileName);

        // Datei herunterladen und lokal speichern
        try (InputStream in = sardine.get("https://ewebdav.pcloud.com" + path)) {
            Files.copy(in, targetFile, StandardCopyOption.REPLACE_EXISTING);
        }

        System.out.println("Downloaded: " + targetFile.toAbsolutePath());
    }
}