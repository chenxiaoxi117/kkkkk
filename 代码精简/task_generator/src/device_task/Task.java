package device_task;


public interface Task  {

	enum FailureReason {
		FAILED_DUE_TO_LATENCY, FAILED_BECAUSE_DEVICE_DEAD, FAILED_DUE_TO_DEVICE_MOBILITY,
		NOT_GENERATED_BECAUSE_DEVICE_DEAD, NO_OFFLOADING_DESTINATIONS, INSUFFICIENT_RESOURCES, INSUFFICIENT_POWER
	}

	/**
	 * Enumeration for status of a Task.
	 */
	enum Status {
		SUCCESS, FAILED
	}

	/**
	 * Returns the maximum latency of the Task.
	 * 
	 * @return the maximum latency of the Task
	 */
	double getMaxLatency();

	/**
	 * Sets the maximum latency of the Task.
	 * 
	 * @param maxLatency the maximum latency of the Task
	 * @return the updated Task
	 */
	Task setMaxLatency(double maxLatency);

	/**
	 * Returns the actual network time of the Task.
	 * 
	 * @return the actual network time of the Task
	 */
	double getActualNetworkTime();

	/**
	 * Adds the actual network time of the Task.
	 * 
	 * @param actualNetworkTime the actual network time of the Task
	 */
	void addActualNetworkTime(double actualNetworkTime);

	/**
	 * Returns the actual CPU time of the Task.
	 * 
	 * @return the actual CPU time of the Task
	 */
	double getActualCpuTime();

	/**
	 * Returns the execution start time of the Task.
	 * 
	 * @return the execution start time of the Task
	 */
	double getExecStartTime();

	/**
	 * Returns the waiting time of the Task.
	 * 
	 * @return the waiting time of the Task
	 */
	double getWatingTime();

	/**
	 * Sets the arrival time of the Task.
	 * 
	 * @param clock the arrival time of the Task
	 */
	void setArrivalTime(double clock);

	/**
	 * Sets the execution start time of the Task.
	 * 
	 * @param clock the execution start time of the Task
	 */
	void setExecutionStartTime(double clock);

	/**
	 * Sets the execution finish time of the Task.
	 * 
	 * @param clock the execution finish time of the Task
	 */
	void setExecutionFinishTime(double clock);

	/**
	 * Sets the ID of the Task.
	 * 
	 * @param id the ID of the Task
	 */
	Task setId(int id);

	/**
	 * Returns the ID of the Task.
	 * 
	 * @return the ID of the Task
	 */
	int getId();

	/**
	 * 
	 * Sets the time of the task.
	 * 
	 * @param time the time to set
	 */
	void setTime(double time);

	/**
	 * 
	 * Gets the time of the task.
	 * 
	 * @return the time of the task
	 */
	double getTime();

	/**
	 * 
	 * Gets the edge device associated with the task.
	 * 
	 * @return the edge device associated with the task
	 */

	/**
	 * 
	 * Sets the edge device associated with the task.
	 * 
	 * @param device the edge device to set
	 * @return the updated Task object
	 */

	/**
	 * 
	 * Sets the container size of the task in bits.
	 * 
	 * @param containerSize the container size to set in bits
	 * @return the updated Task object
	 */
	Task setContainerSizeInBits(double containerSize);

	/**
	 * 
	 * Gets the container size of the task in bits.
	 * 
	 * @return the container size of the task in bits
	 */
	double getContainerSizeInBits();

	/**
	 * 
	 * Gets the container size of the task in megabytes.
	 * 
	 * @return the container size of the task in megabytes
	 */
	double getContainerSizeInMBytes();

	/**
	 * 
	 * Gets the orchestrator associated with the task.
	 * 
	 * @return the orchestrator associated with the task
	 */

	/**
	 * 
	 * Gets the registry associated with the task.
	 * 
	 * @return the registry associated with the task
	 */

	/**
	 * 
	 * Sets the registry associated with the task.
	 * 
	 * @param registry the registry to set
	 * @return the updated Task object
	 */

	/**
	 * 
	 * Gets the ID of the application associated with the task.
	 * 
	 * @return the ID of the application associated with the task
	 */
	int getApplicationID();

	/**
	 * 
	 * Sets the ID of the application associated with the task.
	 * 
	 * @param applicationID the ID of the application to set
	 * @return the updated Task object
	 */
	Task setApplicationID(int applicationID);

	/**
	 * 
	 * Gets the reason for task failure.
	 * 
	 * @return the reason for task failure
	 */
	FailureReason getFailureReason();

	/**
	 * 
	 * Sets the reason for task failure.
	 * 
	 * @param reason the reason for task failure to set
	 */
	void setFailureReason(FailureReason reason);

	/**
	 * 
	 * Gets the offloading destination associated with the task.
	 * 
	 * @return the offloading destination associated with the task
	 */

	/**
	 * 
	 * Sets the offloading destination associated with the task.
	 * 
	 * @param applicationPlacementLocation the offloading destination to set
	 */

	/**
	 * 
	 * Sets the file size of the task request in bits.
	 * 
	 * @param requestSize the file size of the task request to set in bits
	 * @return the updated Task object
	 */
	Task setFileSizeInBits(double requestSize);

	/**
	 * 
	 * Sets the output size of the task in bits.
	 * 
	 * @param outputSize the output size of the task to set in bits
	 * @return the updated Task object
	 */
	Task setOutputSizeInBits(double outputSize);

	/**
	 * 
	 * Gets the length of the task.
	 * 
	 * @return the length of the task
	 */
	double getLength();

	/**
	 * 
	 * Gets the file size of the task request in bits.
	 * 
	 * @return the file size of the task request in bits
	 */
	double getFileSizeInBits();

	/**
	 * 
	 * Gets the output size of the task in bits.
	 * 
	 * @return the output size of the task in bits
	 */
	double getOutputSizeInBits();

	/**
	 * 
	 * Sets the status of the task.
	 * 
	 * @param status the status of the task
	 */
	void setStatus(Status status);

	/**
	 * 
	 * Gets the status of the task.
	 * 
	 * @return the status of the task
	 */
	Status getStatus();

	/**
	 * 
	 * Gets the type of the task.
	 * 
	 * @return the type of the task
	 */
	String getType();

	/**
	 * 
	 * Sets the type of the task.
	 * 
	 * @param type the type of the task
	 * @return the task with the updated type
	 */
	Task setType(String type);

	/**
	 * 
	 * Sets the length of the task.
	 * 
	 * @param length the length of the task
	 * @return the task with the updated length
	 */
	Task setLength(double length);

	/**
	 * 
	 * Sets the orchestrator node of the task.
	 * 
	 * @param orchestrator the orchestrator node of the task
	 */

	/**
	 * 
	 * Gets the total delay of the task.
	 * 
	 * @return the total delay of the task
	 */
	double getTotalDelay();

	/**
	 * 
	 * Sets the serial number of the task.
	 * 
	 * @param l the serial number of the task
	 */
	void setSerial(long l);

	/**
	 * 
	 * Gets the serial number of the task.
	 * 
	 * @return the serial number of the task
	 */
	long getSerial();

	Task setDeviceId(Device dev);



	
}
