package device_task;

class Net_Device{
    String id;
    int deviceid;
    String name;
    String type;
    double latitude;
    double longitude;
    String region; 
    double xPos;
    double yPos;
    String regionInfo;
    String nearestDeviceName;
    String connectivityType;
    double latency;

    public Net_Device(String id, String name, String type,double longitude, double latitude , String region) {
        this.id = id;
        this.name = name;
        this.type = type;
        this.latitude = latitude;
        this.longitude = longitude;
        this.region = region;
    }
    
    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getType() {
        return type;
    }

    public double getLongitude() {
        return longitude;
    }

    public double getLatitude() {
        return latitude;
    }

    public String getregion() {
        return region;
    }
    public String toString() {
        return "Net_Device{" +
                "id='" + id + '\'' +
                ", name='" + name + '\'' +
                ", type='" + type + '\'' +
                ", longitude=" + longitude +
                ", latitude=" + latitude +
                ", region='" + region + '\'' +
                '}';
    }
}