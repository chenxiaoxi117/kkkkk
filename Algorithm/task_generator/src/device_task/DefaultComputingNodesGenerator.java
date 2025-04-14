package device_task;
import java.io.FileReader;
import java.util.List;
import java.util.ArrayList;
import java.util.Random;
import java.util.stream.IntStream;
import java.security.NoSuchAlgorithmException; 
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;


public class DefaultComputingNodesGenerator {
    int TOTAL_DEVICES; 
    protected Random random;
    protected double simulationTime;
    // Get the current working directory of the program
    String currentDirectory = System.getProperty("user.dir");
    File parentDirectory = new File(currentDirectory).getParentFile();
    
    
    public class GeoUtils {
        // Calculate the longitude difference (the change in longitude distance is related to latitude)
        public double calculateLongitudeDifference(double distanceKm, double latitude) {
            double kmPerDegreeLongitude = 111 * Math.cos(Math.toRadians(latitude));
            return distanceKm / kmPerDegreeLongitude;
        }
        // Calculate the latitude difference
        public double calculateLatitudeDifference(double distanceKm) {
            return distanceKm / 111.0;
        }
    }   
    // Method to read CSV and generate configurations
    public  List<ConcentricCircleConfig> readConfigsFromCSV(String filePath) {
        List<ConcentricCircleConfig> configs = new ArrayList<>();
        String line;
        String csvSplitBy = ","; // delimiter
        try (BufferedReader br = new BufferedReader(new FileReader(filePath))) {
            br.readLine(); // Skip the first line of the title
            while ((line = br.readLine()) != null) {
                String[] data = line.split(csvSplitBy);   
                // Extract latitude and longitude (second column), and remove possible spaces and quotes
                String regionInfo = data[0].trim();
                double longitude = Double.parseDouble(data[1].trim());                 
                double latitude = Double.parseDouble(data[2].trim());
                // Extract area (third column), remove quotes
                double area = Double.parseDouble(data[3].trim());
                // Extract device proportion, remove quotes
                double device_proportion = Double.parseDouble(data[4].trim());
                // Use area to calculate radius, and create ConcentricCircleConfig instance
                ConcentricCircleConfig config =
                        new ConcentricCircleConfig(
                            new Location(longitude, latitude),
                            area,
                            0.5, // inner layer proportion
                            0.3, // middle layer proportion
                            0.2, // outer layer proportion
                            device_proportion,   // device percentage
                            regionInfo           // regional information
                        );
                configs.add(config); // Add to configuration list
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        return configs;
    }
    // Method to read CSV and generate network devices
    public  List<Net_Device> readNet_Devicefromcsv(String filePath) {
        List<Net_Device> Net_Devices = new ArrayList<>();
        String line;
        String csvSplitBy = ","; // delimiter
        try (BufferedReader br = new BufferedReader(new FileReader(filePath))) {
            br.readLine(); // Skip the first line of the title
            while ((line = br.readLine()) != null) {
                String[] data = line.split(csvSplitBy);
                String id     = data[0].trim();
                String name   = data[1].trim();
                String type   = data[2].trim(); 
                double longitude = Double.parseDouble(data[3].trim());
                double latitude  = Double.parseDouble(data[4].trim());
                String region    = data[5].trim();
                Net_Device Net_Device = new Net_Device(
                        id,
                        name,
                        type,
                        longitude,
                        latitude,
                        region
                );
                Net_Devices.add(Net_Device); // Add to list
                    
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        
        return Net_Devices;
    }
    
    // Method to get ConcentricCircleConfig array from CSV
    public  ConcentricCircleConfig[] getCircleConfigsFromCSV(String filePath) {
        List<ConcentricCircleConfig> configs = readConfigsFromCSV(filePath);
        return configs.toArray(new ConcentricCircleConfig[0]);
    }
    
    // Method to get Net_Device array from CSV
    public  Net_Device[] getNet_deviceFromCSV(String filePath) {
        List<Net_Device> Net_Devices = readNet_Devicefromcsv(filePath);
        return Net_Devices.toArray(new Net_Device[0]);
    }
   
    // Create a CSV file
    private BufferedWriter csvWriter;
    private static boolean isCsvInitialized = false;
    public void initCsv() throws IOException {
        String relativeFilePath = parentDirectory.getAbsolutePath() + File.separator +"data" + File.separator +"task" + File.separator+ "Device_location.csv";
        String resultFolderPath = parentDirectory.getAbsolutePath() + File.separator +"data" + File.separator +"task";
        File resultFolder = new File(resultFolderPath);
        if (!resultFolder.exists()) {
            resultFolder.mkdirs();
        }
        File csvFile = new File(relativeFilePath);
        boolean fileExists = csvFile.exists();
        if(fileExists) {
        	csvFile.delete(); //before run,making environment no file!
        }
        csvWriter = new BufferedWriter(new FileWriter(csvFile)); 
        // If the file does not exist, write the header
        csvWriter.write("Device ID,X Position,Y Position,Region,Net_device id, connectivityType,latency\n"); 
        csvWriter.flush();  // Flush the data to the file
    }
    private Location generateLocationInEllipse(Random random, double centerX, double centerY, double radiusX, double radiusY) {
        
    	double angle = 2 * Math.PI * random.nextDouble();
        double r = Math.sqrt(random.nextDouble());
        double x = centerX + radiusX * r * Math.cos(angle);
        double y = centerY + radiusY * r * Math.sin(angle);
        return new Location(x, y);
    }
    
    private Location generateLocationInEllipticalRing(Random random, double centerX, double centerY, double innerRadiusX, double innerRadiusY, double outerRadiusX, double outerRadiusY) {
        // Random angle
        double angle = 2 * Math.PI * random.nextDouble();

        // Generate a random radius within the range of inner and outer radii, similar to generateLocationInRing, but consider the ellipse
        double r = Math.sqrt(random.nextDouble() * (outerRadiusX * outerRadiusX - innerRadiusX * innerRadiusX) + innerRadiusX * innerRadiusX);

        // Calculate the offset of the radius in the X and Y directions of the elliptical ring
        double radiusX = innerRadiusX + (outerRadiusX - innerRadiusX) * random.nextDouble();
        double radiusY = innerRadiusY + (outerRadiusY - innerRadiusY) * random.nextDouble();

        // Calculate the offset based on the angle
        double x = centerX + radiusX * r * Math.cos(angle);
        double y = centerY + radiusY * r * Math.sin(angle);
        return new Location(x, y);
    }
    
    // Calculate the distance between two sets of latitude and longitude, return in meters
    public static double haversine(double lat1, double lon1, double lat2, double lon2) {
        double EARTH_RADIUS = 6371e3; // Earth's radius in meters
        double lat1Rad = Math.toRadians(lat1);
        double lat2Rad = Math.toRadians(lat2);
        double deltaLat = Math.toRadians(lat2 - lat1);
        double deltaLon = Math.toRadians(lon2 - lon1);

        double a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
                   Math.cos(lat1Rad) * Math.cos(lat2Rad) *
                   Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return EARTH_RADIUS * c; // Return distance in meters
    }
    
    int[] cityCount = new int[13];  
    int cityIndex = 0;  // Current city index
    int count1=1;
    private int configIndex = 0; // Current configuration index
    
    List<Device> devicesList= new ArrayList<>();; // Use a list of Device type

    public void createComputingNode() throws IOException, NoSuchAlgorithmException {
        // SecureRandom is preferred to generate random values.
        if (!isCsvInitialized) {
            initCsv();
            isCsvInitialized = true; 
        }  
        random = new Random();
        double xPosition = 1;
        double yPosition = 1;
        String relativeFilePath = currentDirectory + File.separator +"data" + File.separator+ "13city.csv";
        Location datacenterLocation = new Location(xPosition, yPosition);
        ConcentricCircleConfig[] circleConfigs = 
                getCircleConfigsFromCSV(relativeFilePath);

        ConcentricCircleConfig config = circleConfigs[configIndex];
        
        // Calculate the corresponding coordinate difference based on the difference in latitude and longitude
        GeoUtils GU = new GeoUtils();
        double latDiffPerKm = GU.calculateLatitudeDifference(1.0);  // Latitude difference corresponding to 1km
        double lonDiffPerKm = GU.calculateLongitudeDifference(1.0, config.center.getYPos());  // Longitude difference corresponding to 1km
        // Convert the radius from kilometers to the projected units
        double adjustedRadiusX_inner = config.innerRadius* lonDiffPerKm;
        double adjustedRadiusY_inner = config.innerRadius* latDiffPerKm;
        // Calculate the radius offset for the middle and outer layers based on the difference in latitude and longitude
        double adjustedRadiusX_middle = config.middleRadius * lonDiffPerKm;
        double adjustedRadiusY_middle = config.middleRadius * latDiffPerKm;
        double adjustedRadiusX_outer = config.outerRadius * lonDiffPerKm;
        double adjustedRadiusY_outer = config.outerRadius * latDiffPerKm;
        // The XPos and YPos of randomPoint will be the planar coordinates after the conversion of latitude and longitude, which can be used directly for maps or further calculations
        int totalDevicesForCurrentConfig = config.getTotalDevicesForCircle(TOTAL_DEVICES,config.percentageOfTotalDevices); // Total number of devices for the current configuration
        int innerCircleLimit = config.getTotalDevicesForCircle(totalDevicesForCurrentConfig, config.innerFraction);
        int middleCircleLimit = config.getTotalDevicesForCircle(totalDevicesForCurrentConfig, config.middleFraction);
        // Randomly generate positions and distinguish different circular layers
        if (cityCount[cityIndex] <= innerCircleLimit) {
            // Generate positions in the inner circle        	
        	datacenterLocation = generateLocationInEllipse(random, 
        			config.center.getXPos(), config.center.getYPos(),
        			adjustedRadiusX_inner, adjustedRadiusY_inner);   
        } else if (cityCount[cityIndex] <= innerCircleLimit + middleCircleLimit) {
            // Generate positions in the middle ring
            datacenterLocation = generateLocationInEllipticalRing(random, 
                    config.center.getXPos(), config.center.getYPos(),
                    adjustedRadiusX_inner, adjustedRadiusY_inner,
                    adjustedRadiusX_middle, adjustedRadiusY_middle);
        } else if (cityCount[cityIndex] <= totalDevicesForCurrentConfig) {
            // Generate positions in the outer ring
            datacenterLocation = generateLocationInEllipticalRing(random, 
                    config.center.getXPos(), config.center.getYPos(),
                    adjustedRadiusX_middle, adjustedRadiusY_middle,
                    adjustedRadiusX_outer, adjustedRadiusY_outer);      
        }
        int deviceId =  count1;  // Start numbering from startingDeviceId     
        // Write the ID and coordinates into the CSV file
        String relativeFilePath1 = currentDirectory + File.separator + "data" + File.separator+"node.csv";
        List<Net_Device> networkDevices = readNet_Devicefromcsv(relativeFilePath1);
        Net_Device nearestDevice = findNearestNetworkDevice(datacenterLocation, networkDevices);
        String connectivityType = assignConnectionType(); 
        double latency = getLatencyBasedOnConnectionType(connectivityType);
        Device newDevice = new Device(String.valueOf(deviceId), "Device_" + deviceId);             
        devicesList.add(newDevice);
        if(deviceId<=TOTAL_DEVICES) {
        	csvWriter.write(deviceId + "," + datacenterLocation.getXPos() + "," + datacenterLocation.getYPos() + "," + config.regionInfo +  
                    "," +nearestDevice.name+ "," + connectivityType + "," + latency+"\n");
            count1++;               
            csvWriter.flush(); // Flush the buffer
        }
        if(deviceId==TOTAL_DEVICES) {
            csvWriter.close(); 
        }
        cityCount[cityIndex]++;
        cityIndex = (cityIndex + 1) % 13;
        configIndex = (configIndex + 1) % circleConfigs.length;
        config = circleConfigs[configIndex];
        totalDevicesForCurrentConfig = config.getTotalDevicesForCircle(TOTAL_DEVICES,config.percentageOfTotalDevices); // Total number of devices for the current configuration
        int attempts=0;
        while (cityCount[cityIndex] >= totalDevicesForCurrentConfig) {
            cityIndex = (cityIndex + 1) % 13;
            configIndex = (configIndex + 1) % circleConfigs.length;
            config = circleConfigs[configIndex];
            totalDevicesForCurrentConfig = config.getTotalDevicesForCircle(TOTAL_DEVICES,config.percentageOfTotalDevices); // Total number of devices for the current configuration
            attempts++;
            if (attempts == 13) {
                break;
            }    
        }
    }
        private Net_Device findNearestNetworkDevice(Location terminalLocation, List<Net_Device> networkDevices) {
            Net_Device nearestDevice = null;
            double minDistance = Double.MAX_VALUE;
            for (Net_Device device : networkDevices) {
                double distance =  haversine(terminalLocation.getYPos(), terminalLocation.getXPos(), 
                                            device.getLatitude(), device.getLongitude());
                if (distance < minDistance) {
                    minDistance = distance;
                    nearestDevice = device;
                }
            }
            return nearestDevice;
        }

        private double getLatencyBasedOnConnectionType(String connectionType) {
            switch (connectionType.toLowerCase()) {
                case "cellular":
                    return 0.01 + Math.random() * (0.03 - 0.01);  // 0.01 - 0.03s
                case "wifi":
                    return 0.001 + Math.random() * (0.005 - 0.001);  // 0.001 - 0.005s
                case "ethernet":
                    return 0.001 + Math.random() * (0.002 - 0.001);  // 0.001 - 0.002s
                default:
                    return 0.0;  // Default latency
            }
        }
	    
	    private String assignConnectionType() {
	        double percentage = (double)count1 / TOTAL_DEVICES; 
	       
	        if (percentage <= 0.30) {
	            return "cellular";  // 30%
	        } else if (percentage <= 0.40) {
	            return "wifi";  // 10%
	        } else if (percentage <= 0.60) {
	            return "ethernet";  // 20%
	        } else {
	            return "wifi";  // 40%
	        }
	    }
	    protected int id = 0;
	    public void generate() {
	        // Get the current working directory of the program
	        // Construct a relative path to save the file in the "src" directory
	        String xmlFilePath = currentDirectory + File.separator + "src" + File.separator + "applications.xml";
	        List<Application> applications = Application.parseApplications(xmlFilePath);
	        // Get simulation time in minutes (excluding the initialization time)
	        simulationTime = 1; // Each device will generate 1 minute of task volume at a rate per minute
	        this.random = new Random();
	        // Remove devices that do not generate
	        devicesList.removeIf(dev -> !dev.isGeneratingTasks());
	        int devicesCount = devicesList.size();
	        // Browse all applications
	        IntStream.range(0, applications.size()-1).forEach(app -> {
	            int numberOfDevices = (int) (applications.get(app).getUsagePercentage()
	                    * devicesCount / 100);
	            IntStream.range(0, numberOfDevices)
	            .mapToObj(i -> {
	                // Randomly remove a device from the device list
	                Device dev = devicesList.remove(random.nextInt(devicesList.size()));
	                dev.setApplicationType(app); // Set the application type
	                return dev; // Return the device
	            })
	            .forEach(dev -> generateTasksForDevice(dev, app, applications));

	        });

	        devicesList.forEach(dev -> generateTasksForDevice(dev, applications.size() - 1, applications));
	    }

	    /**
	     * Generates tasks that will be offloaded during simulation for the given device
	     * and application.
	     *
	     * @param device the device to generate tasks for
	     * @param app    the application type
	     */
	    protected void generateTasksForDevice(Device dev, int app, List<Application> applications) {
	        IntStream.range(0, (int) simulationTime)
	                // First get time in seconds
	                .forEach(st -> insert((st * 60)
	                        // Then pick a random second in this minute "st". Shift the time by a random
	                        // value
	                        + random.nextInt(15), app, dev, applications));
	    }

	    /**
	     * Inserts a task into the task list.
	     *
	     * @param time   the time in seconds at which the task should be executed
	     * @param app    the application type of the task
	     * @param device the device that generates the task
	     */

	    void insert(int time, int app, Device dev, List<Application> applications) {
	        
	        Application appParams = applications.get(app);
	        double requestSize = appParams.getRequestSize();
	        double outputSize = appParams.getResultsSize();
	        double containerSize = appParams.getContainerSizeInBits();
	        double maxLatency = appParams.getLatency();
	        long length = (long) appParams.getTaskLength();
	        int rate = appParams.getRate();
	        int taskDuration = 60 / rate;
	        //System.out.println("re:"+requestSize);
	        for (int i = 0; i < rate; i++) {
	            Task task = new TaskImpl().setId(++id).setType(appParams.getType()).setFileSizeInBits(requestSize)
	                    .setOutputSizeInBits(outputSize).setContainerSizeInBits(containerSize).setApplicationID(app)
	                    .setMaxLatency(maxLatency).setLength(length).setDeviceId(dev);
	            time += taskDuration;
	            task.setTime(time);
	             // Write task information to CSV file
	            writeToCSV(task, dev);
	        }
	    }

	    // Get the last task ID from the CSV file
	    
	    private boolean taskisFirstRun = true;  // A flag to check if it's the first run
	    private void writeToCSV(Task task, Device dev) {
	        // Get the current working directory of the program
	        // Construct a relative path
	        String relativeFilePath = parentDirectory.getAbsolutePath() + File.separator +"data" + File.separator +"task" + File.separator+ "task.csv";
	        String resultFolderPath = parentDirectory.getAbsolutePath() + File.separator +"data" + File.separator +"task";
	        File resultFolder = new File(resultFolderPath);
	        if (!resultFolder.exists()) {
	            resultFolder.mkdirs();
	        }
	        File file = new File(relativeFilePath);

	        // Check if it's the first run and the file exists
	        if (taskisFirstRun && file.exists()) {
	            file.delete();
	            taskisFirstRun = true;  // Set the flag to false after the first run
	        }

	        try (BufferedWriter writer = new BufferedWriter(new FileWriter(relativeFilePath, true))) {
	            // If it's the first run (new file), write the header
	            if (taskisFirstRun) {
	                writer.write("TaskID,AppType,DeviceID,RequestSize,Bandwidth,MaxLatency,Length\n");
	                taskisFirstRun = false;  // After writing the header, mark it as not the first run
	            }
	            // Write task information
	            writer.write(String.format("%d,%s,%s,%f,%f,%f,%f\n",
	                task.getId(),                // Task ID
//	                task.getTime(),              // Task time
	                task.getType(),              // Task type
	                dev.getId(),                 // Device ID
	                task.getFileSizeInBits() * 1, // Request size
	                task.getOutputSizeInBits() * 1, // Output size
//	                task.getContainerSizeInBits() * 1, // Container size
	                task.getMaxLatency(),        // Maximum latency
	                task.getLength()             // Task length
	            ));
	        } catch (IOException e) {
	            e.printStackTrace();
	        }
	    }
 }
