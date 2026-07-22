package pcloud.java.pcloud_service;

import com.github.sardine.DavResource;
import com.github.sardine.Sardine;
import com.github.sardine.SardineFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.List;
import java.time.LocalDate;


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
            LocalDate resDate = res.getModified().toInstant().atZone(java.time.ZoneId.systemDefault()).toLocalDate();
            if (start_date != null && end_date != null && !resDate.isBefore(start_date) && !resDate.isAfter(end_date)) 
                {
                    sb.append(res.isDirectory() ? "[DIR] " : "[FILE] ");
                    sb.append(res.getName());
                    sb.append("\n");
               }
            else if (start_date == null && end_date == null) {
                sb.append(res.isDirectory() ? "[DIR] " : "[FILE] ");
                sb.append(res.getName());
                sb.append("\n");
            }
        }
        System.out.println("Files at " + path + " between " + start_date + " and " + end_date + ":\n" + sb);
        return sb.toString();
    }
}