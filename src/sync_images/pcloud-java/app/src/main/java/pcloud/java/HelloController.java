package pcloud.java;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestParam;
import java.io.IOException;
import java.time.LocalDate;

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

    @GetMapping("/download_file")
    public String downloadBatch(
        @RequestParam(defaultValue = "/Automatic%20Upload/Samsung%20SM-M356B/20250415_173150.jpg") String path
    ) throws IOException {
        // Call the downloadBatch method from the DownloadService class
        downloadService.downloadFile(path);

        // print a message to the console indicating that the downloadBatch endpoint was called
        System.out.println("downloadFile endpoint called.");

        return "Download successful.";
    }

    @GetMapping("/list_files")
    public String listFiles(
        @RequestParam(defaultValue = "/Automatic%20Upload/Samsung%20SM-M356B/") String path,
        @RequestParam(required = false) LocalDate start_date,
        @RequestParam(required = false) LocalDate end_date) throws IOException {
        // Call the listFiles method from the ListService class
        String result = listService.listFiles(path, start_date, end_date);

        // print a message to the console indicating that the listFiles endpoint was called
        System.out.println("listFiles endpoint called.");

        // print result to the console
        System.out.println("Result from listFiles: " + result);

        return result;
    }
        
}
