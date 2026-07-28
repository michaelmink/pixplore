package pcloud.java.pcloud_service;

import pcloud.java.chroma_service.ChromaService;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import com.github.sardine.DavResource;
import com.github.sardine.Sardine;
import com.github.sardine.SardineFactory;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.List;
import java.time.LocalDate;


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

    public void downloadFiles(
        String path,
        Boolean trigger_download,
        java.time.LocalDate start_date, 
        java.time.LocalDate end_date, 
        String ignore_existing,
        int limit) throws IOException {
        System.out.println("Downloading Files from: " + path + " to " + downloadPath);
        System.out.println("Start Date: " + start_date);
        System.out.println("End Date: " + end_date);
        System.out.println("Ignore Existing: " + ignore_existing);
        System.out.println("Limit: " + limit);
        
        // ChromaService.checkFileExists
        ChromaService chromaService = new ChromaService();
        String sampleFile = "example.txt";
        boolean fileExists = chromaService.checkFileExists(sampleFile);
        System.out.println("File " + sampleFile + " exists in ChromaDB: " + fileExists);

        // connect to pCloud using Sardine
        Sardine sardine = SardineFactory.begin(username, password);
        List<DavResource> resources = sardine.list("https://ewebdav.pcloud.com" + path);

        StringBuilder sb = new StringBuilder();
        int limitCounter = 0;

        // filter by date if start_date and end_date are provided   
        for (DavResource res : resources) {
            // stop if limit is reached
            if (limitCounter >= limit) {
                break;
            }
            
            // get the modified date of the resource and convert it to LocalDate
            LocalDate resDate = res.getModified().toInstant().atZone(java.time.ZoneId.systemDefault()).toLocalDate();

            if (!resDate.isBefore(start_date) && !resDate.isAfter(end_date)) 
                {
                    if (!res.isDirectory()) {
                        // check if file is already processed and should be ignored
                        if (ignore_existing.equals(true))
                        {
                            // check in ChromaDB if the file has already been processed
                            // if it has, skip it
                            // if it hasn't, add it to the list of files to download

                        }
                        sb.append(res.getName() + "\n");

                        limitCounter++;
                    }
               }
        }

        System.out.println("Files at " + path + " between " + start_date + " and " + end_date + ":\n" + sb);

        // download the files that match the criteria
        if (trigger_download) {
            for (String fileName : sb.toString().split("\n")) {
                    String filePath = path + fileName;
                    downloadFile(filePath);
            }
        }
    }
}