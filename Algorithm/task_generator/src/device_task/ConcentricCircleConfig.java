package device_task;

class ConcentricCircleConfig {
    Location center;
    double innerRadius;
    double middleRadius;
    double outerRadius;     
    double innerFraction;
    double middleFraction;
    double outerFraction;
    double percentageOfTotalDevices; // Percentage of total devices
    String regionInfo;  // Regional information field

    public ConcentricCircleConfig(Location center, double area, 
            double innerFraction, double middleFraction, 
            double outerFraction, double percentageOfTotalDevices,
            String regionInfo) {
        this.center = center;
        this.outerRadius = Math.sqrt(area / Math.PI);  // Radius of the outer circle
        this.middleRadius = outerRadius * 2 / 3;  // Radius of the middle circle
        this.innerRadius = outerRadius / 3;  // Radius of the inner circle
        this.innerFraction = innerFraction;
        this.middleFraction = middleFraction;
        this.outerFraction = outerFraction;
        this.percentageOfTotalDevices = percentageOfTotalDevices;
        this.regionInfo = regionInfo;
    }

    // Method to retrieve regional information
    public String getRegionInfo() {
        return regionInfo;
    }

    public int getTotalDevicesForCircle(int totalDevices, double fraction) {
        return (int) (totalDevices * fraction);
    }
}
