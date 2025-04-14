package device_task;

public class Device {
    private String id; // Device ID
    private String name; // Device name
    private boolean generatingTasks; // Whether the device generates tasks
    private int applicationType; // Current application type

    // Constructor
    public Device(String id, String name) {
        this.id = id;
        this.name = name;
        this.generatingTasks = true; // Default to generating tasks
    }

    // Get device ID
    public String getId() {
        return id;
    }

    // Get device name
    public String getName() {
        return name;
    }

    // Check if the device generates tasks
    public boolean isGeneratingTasks() {
        return generatingTasks;
    }

    // Set whether the device generates tasks
    public void setGeneratingTasks(boolean generatingTasks) {
        this.generatingTasks = generatingTasks;
    }

    // Get the current application type
    public int getApplicationType() {
        return applicationType;
    }

    // Set the application type
    public void setApplicationType(int applicationType) {
        this.applicationType = applicationType;
    }

    @Override
    public String toString() {
        return "Device{" +
                "id='" + id + '\'' +
                ", name='" + name + '\'' +
                ", generatingTasks=" + generatingTasks +
                ", applicationType=" + applicationType +
                '}';
    }
}