package pcloud.java.pcloud_service;

import com.github.sardine.DavResource;
import com.github.sardine.Sardine;
import com.github.sardine.SardineFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.List;
import java.time.LocalDate;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;


@Service
public class ListService {

    @Value("${pcloud.api.username}")
    private String username;

    @Value("${pcloud.api.password}")
    private String password;

    public String listFiles(String path, LocalDate start_date, LocalDate end_date) throws IOException {
        // connect to pCloud using Sardine
        Sardine sardine = SardineFactory.begin(username, password);
        List<DavResource> resources = sardine.list("https://ewebdav.pcloud.com" + path);

        StringBuilder sb = new StringBuilder();

        // filter by date if start_date and end_date are provided   
        for (DavResource res : resources) {
            // get Date from res.getModified() and convert to LocalDate
            LocalDate resDate = res.getModified().toInstant().atZone(java.time.ZoneId.systemDefault()).toLocalDate();
            // skip if it's a directory
            if (res.isDirectory()) {
                continue;
            }
            // check if resDate is between start_date and end_date
            if (start_date != null && end_date != null && resDate.isAfter(start_date) && resDate.isBefore(end_date))
                {
                    sb.append(path).append(res.getName());
                    sb.append("\n");
               }
            else if (start_date == null && end_date == null) {
                sb.append(path).append(res.getName());
                sb.append("\n");
            }
        }
        System.out.println("Files at " + path + " between " + start_date + " and " + end_date + ":\n" + sb);
        return sb.toString();
    }

    public void removeLocalFile(String filePath) throws IOException {
        Path targetFile = Paths.get(filePath);
        if (Files.exists(targetFile)) {
            Files.delete(targetFile);
            System.out.println("Deleted local file: " + targetFile.toAbsolutePath());
        } else {
            System.out.println("Local file does not exist: " + targetFile.toAbsolutePath());
        }
    }
}