
from openf1_client import get_session, get_driver_telemetry, get_circuit_corners

print("Connecting to OpenF1...")

session = get_session(2024, "Monza", "Q")

print("\nSession found!")
print("Session details:")
print(session)

print("\nRetrieving Charles Leclerc telemetry...")

result = get_driver_telemetry(
    session["session_key"],
    "LEC"
)

print("\nDriver:")
print(result["driver"]["full_name"])

print("\nFastest lap:")
print(result["lap"]["lap_duration"], "seconds")

print("\nTelemetry preview:")
print(
    result["telemetry"][
        ["Distance", "Speed", "Throttle", "Brake", "nGear"]
    ].head()
)

#this is new line
print("\nRetrieving circuit corners...")

corners = get_circuit_corners(session)

for corner in corners:
    print(
        f"Turn {corner['label']}: "
        f"{corner['distance']:.1f} m"
    )
    
print("\nOpenF1 connection successful!")