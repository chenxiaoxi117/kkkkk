package device_task;


public class Location {
	protected double xPos;
	protected double yPos;

	public Location(double xPos, double yPos) {
		this.xPos = xPos;
		this.yPos = yPos;
	}

	public double getXPos() {
		return xPos;
	}

	public double getYPos() {
		return yPos;
	}

	@Override
	public boolean equals(Object o) {
		if (this == o) {
			return true;
		}
		if (o == null || getClass() != o.getClass()) {
			return false;
		}

		Location other = (Location) o;
		return (this.xPos == other.xPos && this.yPos == other.yPos);
	}
	@Override
	public int hashCode() {
		int hash = 7;
		hash = hash(hash, toBits(this.xPos));
		return hash(hash, toBits(this.yPos));
	}

	protected int hash(final int hash, final int value) {
		return 89 * hash + value;
	}

	protected int toBits(final double value) {
		return (int) (Double.doubleToLongBits(value) ^ (Double.doubleToLongBits(value) >>> 32));
	}
}
