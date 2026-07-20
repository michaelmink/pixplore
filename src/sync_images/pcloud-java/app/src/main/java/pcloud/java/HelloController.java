package pcloud.java;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestParam;
import java.io.IOException;

import pcloud.java.pcloud_service.DownloadService;
import pcloud.java.pcloud_service.ListService;


@RestController
public class HelloController {

    private final DownloadService downloadService;
    private final ListService listService;

    public HelloController(DownloadService downloadService, ListService listService) {
        this.downloadService = downloadService;
        this.listService = listService;
    }
    


    @GetMapping("/health")
    public String health() {
        return "Healthy";
    }

    @GetMapping("/download_batch")
    public String downloadBatch() {
        // Call the downloadBatch method from the DownloadService class
        downloadService.downloadBatch();

        // print a message to the console indicating that the downloadBatch endpoint was called
        System.out.println("downloadBatch endpoint called.");

        return "Download successful.";
    }

    @GetMapping("/list_files")
    public String listFiles(@RequestParam(defaultValue = "/") String path) throws IOException {
        // Call the listFiles method from the ListService class
        String result = listService.listFiles(path);

        // print a message to the console indicating that the listFiles endpoint was called
        System.out.println("listFiles endpoint called.");

        // print result to the console
        System.out.println("Result from listFiles: " + result);

        return result;
    }
        
}
