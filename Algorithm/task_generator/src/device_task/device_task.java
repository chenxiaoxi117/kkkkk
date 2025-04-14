package device_task;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.security.NoSuchAlgorithmException;

public class device_task {
    public static void main(String[] args) throws NoSuchAlgorithmException, IOException {
        int totalDevices = 5000; // Default number of devices, can be overridden by command-line arguments
        // Check if the number of devices is provided as a command-line argument
        if (args.length > 0 && !args[0].equals("none")) {  
            totalDevices = Integer.parseInt(args[0]);
        }      
        // Log the start time of the program
        long startTime = System.currentTimeMillis();
        DefaultComputingNodesGenerator generator = new DefaultComputingNodesGenerator();
        generator.TOTAL_DEVICES = totalDevices; // Set the total number of devices
        int createdDevices = 0; // Counter for the number of devices created
        // Generate devices
        while (createdDevices < totalDevices) {
        	generator.createComputingNode();
        	createdDevices++;
        }
        // Generate tasks
        generator.generate();
        // Read the CSV file and count the number of lines (tasks)
        String currentDirectory = System.getProperty("user.dir");
        File parentDirectory = new File(currentDirectory).getParentFile();
//        String csvFilePath = currentDirectory + File.separator +"result" + File.separator+ "tasks.csv";
        String csvFilePath = parentDirectory.getAbsolutePath() + File.separator +"data" + File.separator +"task" + File.separator+ "task.csv";
        long lineCount = -1;
        try (BufferedReader reader = new BufferedReader(new FileReader(csvFilePath))) {
            while (reader.readLine() != null) {
                lineCount++;
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        // Log the end time and calculate the duration
        long endTime = System.currentTimeMillis();
        long duration = endTime - startTime; // Duration in milliseconds
        // Print the summary to the console
        System.out.println("Total devices created: " + createdDevices);
        System.out.println("Total tasks generated: " + lineCount);
        System.out.println("Total execution time: " + duration / 1000 + " seconds");
    }
}
