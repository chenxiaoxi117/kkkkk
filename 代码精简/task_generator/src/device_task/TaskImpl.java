package device_task;

public class TaskImpl implements Task {

    private int id;
    private double maxLatency;
    private double actualNetworkTime;
    private double actualCpuTime;
    private double execStartTime;
    private double waitingTime;
    private double time;
    private double containerSize;
    private double fileSize;
    private double outputSize;
    private double length;
    private Status status;
    private String type;
    private int applicationID;
    private long serial;
    private Device device;
    
    // Implementing the methods from Task interface
    @Override
    public double getMaxLatency() {
        return maxLatency;
    }

    @Override
    public Task setMaxLatency(double maxLatency) {
        this.maxLatency = maxLatency;
        return this;
    }

    @Override
    public double getActualNetworkTime() {
        return actualNetworkTime;
    }

    @Override
    public void addActualNetworkTime(double actualNetworkTime) {
        this.actualNetworkTime += actualNetworkTime;
    }

    @Override
    public double getActualCpuTime() {
        return actualCpuTime;
    }

    @Override
    public double getExecStartTime() {
        return execStartTime;
    }

    @Override
    public double getWatingTime() {
        return waitingTime;
    }

    @Override
    public void setArrivalTime(double clock) {
        this.waitingTime = clock;
    }

    @Override
    public void setExecutionStartTime(double clock) {
        this.execStartTime = clock;
    }

    @Override
    public void setExecutionFinishTime(double clock) {
        // Logic to set the finish time
    }

    @Override
   
    public Task setId(int id) {
        this.id = id;
        return this; 
    }

    @Override
    public int getId() {
        return id;
    }

    @Override
    public void setTime(double time) {
        this.time = time;
    }

    @Override
    public double getTime() {
        return time;
    }

    @Override
    public Task setContainerSizeInBits(double containerSize) {
        this.containerSize = containerSize;
        return this;
    }

    @Override
    public double getContainerSizeInBits() {
        return containerSize;
    }

    @Override
    public double getContainerSizeInMBytes() {
        return containerSize / 8_000_000.0; // Convert from bits to megabytes
    }

    @Override
    public Task setFileSizeInBits(double requestSize) {
        this.fileSize = requestSize;
        return this;
    }

    @Override
    public Task setOutputSizeInBits(double outputSize) {
        this.outputSize = outputSize;
        return this;
    }

    @Override
    public double getLength() {
        return length;
    }

    @Override
    public Task setLength(double length) {
        this.length = length;
        return this;
    }

    @Override
    public Task setType(String type) {
        this.type = type;
        return this;
    }

    @Override
    public String getType() {
        return type;
    }

    @Override
    public void setStatus(Status status) {
        this.status = status;
    }

    @Override
    public Status getStatus() {
        return status;
    }

    @Override
    public int getApplicationID() {
        return applicationID;
    }

    @Override
    public Task setApplicationID(int applicationID) {
        this.applicationID = applicationID;
        return this;
    }

    @Override
    public void setSerial(long serial) {
        this.serial = serial;
    }

    @Override
    public long getSerial() {
        return serial;
    }

    @Override
    public double getFileSizeInBits() {
        return fileSize;
    }

    @Override
    public double getOutputSizeInBits() {
        return outputSize;
    }

    @Override
    public double getTotalDelay() {
        // Implement the logic for total delay calculation if necessary
        return 0;
    }

    @Override
    public FailureReason getFailureReason() {
        // Return failure reason, implement logic if necessary
        return null;
    }

    @Override
    public void setFailureReason(FailureReason reason) {
        // Set failure reason, implement logic if necessary
    }

   
 // Set the device
    public Task setDevice(Device device) {
        this.device = device;
        return this; // Return the current object to support method chaining
    }

    // Get the device
    public Device getDevice() {
        return device;
    }

    private String deviceId; // Device ID

    // Set the device ID
    public Task setDeviceId(Device device) {
        this.deviceId = device.getId(); // Retrieve the device's ID
        this.device = device; // Store the device object (if needed)
        return this; // Return the current object to support method chaining
    }

}

	

   

