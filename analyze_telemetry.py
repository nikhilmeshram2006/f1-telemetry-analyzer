
import argparse
import os

import matplotlib.pyplot as plt

from openf1_client import (
    get_session,
    get_driver_telemetry,
    get_circuit_corners
)


def format_laptime(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    return f"{minutes}:{remaining_seconds:06.3f}"


def get_driver_color(driver, fallback):
    color = driver.get("team_colour")

    if not color:
        return fallback

    color = str(color).strip()

    if not color.startswith("#"):
        color = f"#{color}"

    return color




def add_corner_annotations(axes, corners, max_distance):
    """Add compact circuit corner markers to telemetry plots."""

    label_levels = [-5, -17, -29]

    for index, corner in enumerate(corners):
        distance = corner["distance"]
        label = corner["label"]

        if distance < 0 or distance > max_distance:
            continue

        # Draw subtle vertical guide lines.
        for axis in axes:
            axis.axvline(
                x=distance,
                color="#AAAAAA",
                linestyle=":",
                linewidth=0.7,
                alpha=0.25,
                zorder=0
            )

        # Alternate between three label heights.
        label_height = label_levels[index % 3]

        axes[0].annotate(
            f"T{label}",
            xy=(distance, 1),
            xycoords=("data", "axes fraction"),
            xytext=(0, label_height),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=7,
            color="#DDDDDD",
            alpha=0.9,
            annotation_clip=False
        )




def plot_telemetry_comparison(
    year,
    event,
    session_type,
    driver1_code,
    driver2_code,
    output_file
):
    print(f"Loading {year} {event} ({session_type})...")

    # Find the requested session.
    session = get_session(year, event, session_type)

    session_key = session["session_key"]

    # Retrieve telemetry for both drivers.
    print(f"Retrieving telemetry for {driver1_code}...")

    driver1_data = get_driver_telemetry(
        session_key,
        driver1_code
    )

    print(f"Retrieving telemetry for {driver2_code}...")

    driver2_data = get_driver_telemetry(
        session_key,
        driver2_code
    )

    # Retrieve circuit corner information.
    print("Retrieving circuit corners...")

    try:
        corners = get_circuit_corners(session)
        print(f"Retrieved {len(corners)} circuit corners.")

    except (RuntimeError, ValueError, KeyError) as error:
        print(f"Corner annotations unavailable: {error}")
        corners = []

    driver1 = driver1_data["driver"]
    driver2 = driver2_data["driver"]

    telemetry1 = driver1_data["telemetry"]
    telemetry2 = driver2_data["telemetry"]

    lap1 = driver1_data["lap"]
    lap2 = driver2_data["lap"]

    # Get official team colours.
    color1 = get_driver_color(driver1, "#E10600")
    color2 = get_driver_color(driver2, "#00D2BE")

    name1 = driver1.get("name_acronym", driver1_code)
    name2 = driver2.get("name_acronym", driver2_code)

    # Create the graph.
    plt.style.use("dark_background")

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(16, 13),
        sharex=True
    )

    fig.patch.set_facecolor("#15151E")

    for axis in axes:
        axis.set_facecolor("#1F1F2B")

        axis.grid(
            True,
            color="#555566",
            linestyle="--",
            alpha=0.35
        )

        axis.tick_params(colors="white")

        for spine in axis.spines.values():
            spine.set_color("#555566")

    # Speed.
    axes[0].plot(
        telemetry1["Distance"],
        telemetry1["Speed"],
        color=color1,
        label=name1,
        linewidth=1.5
    )

    axes[0].plot(
        telemetry2["Distance"],
        telemetry2["Speed"],
        color=color2,
        label=name2,
        linewidth=1.5
    )

    axes[0].set_ylabel("Speed (km/h)")

    axes[0].set_title(
        "F1 TELEMETRY COMPARISON",
        color="white",
        fontsize=16,
        fontweight="bold",
        pad=15
    )

    axes[0].legend(
        facecolor="#292938",
        edgecolor="#555566"
    )

    # Throttle.
    axes[1].plot(
        telemetry1["Distance"],
        telemetry1["Throttle"],
        color=color1,
        linewidth=1.5
    )

    axes[1].plot(
        telemetry2["Distance"],
        telemetry2["Throttle"],
        color=color2,
        linewidth=1.5
    )

    axes[1].set_ylabel("Throttle (%)")
    axes[1].set_ylim(-5, 105)

    # Brake.
    axes[2].step(
        telemetry1["Distance"],
        telemetry1["Brake"].astype(int),
        color=color1,
        where="post",
        linewidth=1.5
    )

    axes[2].step(
        telemetry2["Distance"],
        telemetry2["Brake"].astype(int),
        color=color2,
        where="post",
        linewidth=1.5
    )

    axes[2].set_ylabel("Brake")
    axes[2].set_yticks([0, 1])
    axes[2].set_yticklabels(["Off", "On"])

    # Gear.
    axes[3].step(
        telemetry1["Distance"],
        telemetry1["nGear"],
        color=color1,
        where="post",
        linewidth=1.5
    )

    axes[3].step(
        telemetry2["Distance"],
        telemetry2["nGear"],
        color=color2,
        where="post",
        linewidth=1.5
    )

    axes[3].set_ylabel("Gear")
    axes[3].set_xlabel("Distance (m)")

    # Add circuit corner annotations.
    max_distance = max(
        telemetry1["Distance"].max(),
        telemetry2["Distance"].max()
    )

    add_corner_annotations(
        axes,
        corners,
        max_distance
    )

    # Add lap information.
    lap_info = (
        f"{name1}: {format_laptime(lap1['lap_duration'])}    "
        f"{name2}: {format_laptime(lap2['lap_duration'])}"
    )

    fig.text(
        0.5,
        0.015,
        lap_info,
        ha="center",
        color="#CCCCCC",
        fontsize=10
    )

    fig.tight_layout(rect=[0, 0.04, 1, 1])

    # Save the graph.
    output_directory = os.path.dirname(output_file)

    if output_directory:
        os.makedirs(output_directory, exist_ok=True)

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight",
        facecolor=fig.get_facecolor()
    )

    plt.close(fig)

    print("\nTelemetry comparison completed!")
    print(f"Driver 1: {driver1.get('full_name', name1)}")
    print(f"Driver 2: {driver2.get('full_name', name2)}")
    print(f"Saved graph: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare Formula 1 driver telemetry using OpenF1."
    )

    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--gp", type=str, default="Monza")
    parser.add_argument("--session", type=str, default="Q")
    parser.add_argument("--d1", type=str, default="LEC")
    parser.add_argument("--d2", type=str, default="PIA")

    parser.add_argument(
        "--out",
        type=str,
        default="telemetry_comparison.png"
    )

    args = parser.parse_args()

    try:
        plot_telemetry_comparison(
            args.year,
            args.gp,
            args.session,
            args.d1,
            args.d2,
            args.out
        )

    except (RuntimeError, ValueError, KeyError) as error:
        print(f"\nError: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
