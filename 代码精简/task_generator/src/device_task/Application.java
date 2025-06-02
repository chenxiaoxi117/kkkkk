package device_task;

import org.w3c.dom.*;

import javax.xml.parsers.*;
import java.io.*;
import java.util.ArrayList;
import java.util.List;

/**
 * This class represents an application that can be executed on a computing
 * node.
 * 
 * 
 **/

public class Application {

	/**
	 * The rate at which requests are generated for this application
	 */
	protected int rate;

	/**
	 * The latency of the application, in seconds
	 */
	protected double latency;

	/**
	 * The size of the container that this application runs in, in bits
	 */
	protected double containerSize;

	/**
	 * The size of the request that is sent to the application, in bits
	 */
	protected double requestSize;

	/**
	 * The size of the results that the application returns, in bits
	 */
	protected double resultsSize;

	/**
	 * The length of time it takes for the application to execute, in MI
	 * (Mega-Instructions)
	 */
	protected double taskLength;

	/**
	 * The percentage of time that the application is being used by the user
	 */
	protected double usagePercentage;

	/**
	 * The type of application
	 */
	protected String type;

	/**
	 * The number of bits in one megabyte.
	 */
	private static final double BITS_IN_MB = 8000000.0;

	/**
	 * Constructs a new Application object.
	 *
	 * @param type            the type of the application
	 * @param rate            the rate at which requests are generated for this
	 *                        application
	 * @param usagePercentage the percentage of time that the application is being
	 *                        used by the user
	 * @param latency         the latency of the  application, in seconds
	 * @param containerSize2   the size of the container that this application runs
	 *                        in, in bits
	 * @param requestSize2     the size of the request that is sent to the
	 *                        application, in bits
	 * @param resultsSize2     the size of the results that the application returns,
	 *                        in bits
	 * @param taskLength      the length of time it takes for the application to
	 *                        execute, in MI (Mega-Instructions)
	 */
	
	public Application(String type, int rate, double usagePercentage, double latency, double containerSize2,
			double requestSize2, double resultsSize2, double taskLength) {
		setType(type);		setRate(rate);
		setUsagePercentage(usagePercentage);
		setLatency(latency);
		setContainerSize(containerSize2);
		setRequestSize(requestSize2);
		setResultsSize(resultsSize2);
		setTaskLength(taskLength);
	}

	/**
	 * Gets the rate at which requests are generated for this application.
	 *
	 * @return the rate at which requests are generated for this application
	 */
	public int getRate() {
		return rate;
	}

	/**
	 * Sets the rate at which requests are generated for this application.
	 *
	 * @param rate the rate at which requests are generated for this application
	 */
	public void setRate(int rate) {
		this.rate = rate;
	}

	/**
	 * 
	 * Returns the size of the container in bits.
	 * 
	 * @return the size of the container in bits
	 */
	public double getContainerSizeInBits() {
		return containerSize;
	}

	/**
	 * 
	 * Sets the size of the container in bits.
	 * 
	 * @param containerSize the size of the container in bits
	 */
	public void setContainerSize(double containerSize) {
		this.containerSize = containerSize;
	}

	/**
	 * 
	 * Returns the size of the request in bits.
	 * 
	 * @return the size of the request in bits
	 */
	public double getRequestSize() {
		return requestSize;
	}

	/**
	 * 
	 * Sets the size of the request in bits.
	 * 
	 * @param requestSize the size of the request in bits
	 */
	public void setRequestSize(double requestSize) {
		this.requestSize = requestSize;
	}

	/**
	 * 
	 * Returns the length of the task in MI.
	 * 
	 * @return the length of the task in MI
	 */
	public double getTaskLength() {
		return taskLength;
	}

	/**
	 * 
	 * Sets the length of the task in MI.
	 * 
	 * @param taskLength the length of the task in MI
	 */
	public void setTaskLength(double taskLength) {
		this.taskLength = taskLength;
	}

	/**
	 * 
	 * Returns the size of the results in bits.
	 * 
	 * @return the size of the results in bits
	 */
	public double getResultsSize() {
		return resultsSize;
	}

	/**
	 * 
	 * Sets the size of the results in bits.
	 * 
	 * @param resultsSize2 the size of the results in bits
	 */
	public void setResultsSize(double resultsSize2) {
		this.resultsSize = resultsSize2;
	}

	/**
	 * 
	 * Returns the usage percentage of the application.
	 * 
	 * @return the usage percentage of the application
	 */
	public double getUsagePercentage() {
		return usagePercentage;
	}

	/**
	 * 
	 * Sets the usage percentage of the application.
	 * 
	 * @param usagePercentage the usage percentage of the application
	 */
	public void setUsagePercentage(double usagePercentage) {
		this.usagePercentage = usagePercentage;
	}

	/**
	 * 
	 * Returns the latency of the application in seconds.
	 * 
	 * @return the latency of the application in seconds
	 */
	public double getLatency() {
		return latency;
	}

	/**
	 * 
	 * Sets the latency of the application in seconds.
	 * 
	 * @param latency the latency of the application in seconds
	 */
	public void setLatency(double latency) {
		this.latency = latency;
	}

	/**
	 * 
	 * Returns the type of the application.
	 * 
	 * @return the type of the application
	 */
	public String getType() {
		return type;
	}

	/**
	 * 
	 * Sets the type of the application.
	 * 
	 * @param type the type of the application
	 */
	public void setType(String type) {
		this.type = type;
	}

	/**
	 * 
	 * Returns the size of the container in megabytes.
	 * 
	 * @return the size of the container in megabytes
	 */
	public double getContainerSizeInMBytes() {
		return containerSize / BITS_IN_MB;
	}

	/**
	 * 
	 * Returns a string representation of the Application object.
	 * 
	 * @return a string representation of the Application object
	 */
	@Override
	public String toString() {
		return "Application [type=" + type + ", rate=" + rate + ", latency=" + latency + ", containerSize="
				+ containerSize + ", requestSize=" + requestSize + ", resultsSize=" + resultsSize + ", taskLength="
				+ taskLength + ", usagePercentage=" + usagePercentage + "]";
	}
	
	 public static List<Application> parseApplications(String filePath) {
	        List<Application> applications = new ArrayList<>();
	        try {
	            File inputFile = new File(filePath);
	            DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
	            DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
	            Document doc = dBuilder.parse(inputFile);
	            doc.getDocumentElement().normalize();

	            NodeList nList = doc.getElementsByTagName("application");

	            for (int temp = 0; temp < nList.getLength(); temp++) {
	                Node nNode = nList.item(temp);
	                if (nNode.getNodeType() == Node.ELEMENT_NODE) {
	                    Element element = (Element) nNode;

	                    String name = element.getAttribute("name");
	                    String type = element.getElementsByTagName("type").item(0).getTextContent();
	                    int rate = Integer.parseInt(element.getElementsByTagName("rate").item(0).getTextContent());
	                    double usagePercentage = Double.parseDouble(element.getElementsByTagName("usage_percentage").item(0).getTextContent());
	                    double latency = Double.parseDouble(element.getElementsByTagName("latency").item(0).getTextContent());
	                    double containerSize = Double.parseDouble(element.getElementsByTagName("container_size").item(0).getTextContent());
	                    double requestSize = Double.parseDouble(element.getElementsByTagName("request_size").item(0).getTextContent());
	                    double resultsSize = Double.parseDouble(element.getElementsByTagName("results_size").item(0).getTextContent());
	                    double taskLength = Double.parseDouble(element.getElementsByTagName("task_length").item(0).getTextContent());
	                    Application app = new Application(type, rate, usagePercentage, latency, containerSize, requestSize, resultsSize, taskLength);
	                    applications.add(app);
	                }
	            }
	        } catch (Exception e) {
	            e.printStackTrace();
	        }
	        return applications;
	    }}
