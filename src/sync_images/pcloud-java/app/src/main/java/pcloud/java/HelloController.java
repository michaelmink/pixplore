package pcloud.java;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestParam;
import java.io.IOException;
import java.time.LocalDate;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

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
        @RequestParam(defaultValue = "/Automatic%20Upload/Samsung%20SM-M356B/20250415_173150.jpg") String path,
        @RequestParam(defaultValue = "/tmp/images") String output_path
    ) throws IOException {
        // Call the downloadBatch method from the DownloadService class
        downloadService.downloadFile(path, output_path);

        // print a message to the console indicating that the downloadBatch endpoint was called
        System.out.println("downloadFile endpoint called.");

        return "Download successful.";
    }

    @GetMapping("/list_files")
    public String listFiles(
        @RequestParam(defaultValue = "/Automatic%20Upload/Samsung%20SM-M356B/") String path,
        @RequestParam(required = false) LocalDate start_date,
        @RequestParam(required = false) LocalDate end_date,
        @RequestParam(defaultValue = "/tmp/images/list_files.csv") String output_path,
        @RequestParam(required = true, defaultValue = "false") Boolean trigger_download,
        @RequestParam(required = false) Integer limit
    ) throws IOException {
        // Call the listFiles method from the ListService class
        String result = listService.listFiles(path, start_date, end_date);

        // print a message to the console indicating that the listFiles endpoint was called
        System.out.println("listFiles endpoint called.");

        // apply limit if exists
        if (limit != null && limit > 0) {
            String[] lines = result.split("\n");
            StringBuilder limitedResult = new StringBuilder();
            for (int i = 0; i < Math.min(limit, lines.length); i++) {
                limitedResult.append(lines[i]).append("\n");
            }
            result = limitedResult.toString();
        }

        // print result to the console
        System.out.println("Result from listFiles: " + result);

        // save to a file in /tmp/images/list_files.csv
        if (trigger_download) {
            Path outputPath = Paths.get(output_path);
            Files.createDirectories(outputPath.getParent());
            Files.write(outputPath, result.getBytes());
        }

        return result;
    }

    @GetMapping("/remove_local_file")
    public String removeFile(
        @RequestParam(defaultValue = "/tmp/images/img.jpg") String path
    ) throws IOException {
        // Call the removeFile method from the DownloadService class
        listService.removeLocalFile(path);

        // print a message to the console indicating that the removeFile endpoint was called
        System.out.println("removeFile endpoint called.");

        return "Remove successful.";
    }
}
