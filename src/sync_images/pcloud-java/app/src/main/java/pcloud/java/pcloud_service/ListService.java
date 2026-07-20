package pcloud.java.pcloud_service;

import com.github.sardine.DavResource;
import com.github.sardine.Sardine;
import com.github.sardine.SardineFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.List;

@Service
public class ListService {

    @Value("${pcloud.api.username}")
    private String username;

    @Value("${pcloud.api.password}")
    private String password;

    public String listFiles(String path) throws IOException {
        Sardine sardine = SardineFactory.begin(username, password);
        List<DavResource> resources = sardine.list("https://ewebdav.pcloud.com" + path);

        StringBuilder sb = new StringBuilder();
        for (DavResource res : resources) {
            sb.append(res.isDirectory() ? "[DIR] " : "[FILE] ");
            sb.append(res.getName());
            //sb.append(" (").append(res.getContentLength()).append(" bytes)");
            sb.append("\n");
        }

        System.out.println("Files at " + path + ":\n" + sb);
        return sb.toString();
    }
}