
from openf1_client import get_session, fetch_data

session = get_session(2024, "Monza", "Q")

drivers = fetch_data(
    "drivers",
    {"session_key": session["session_key"]}
)

print("\n2024 MONZA QUALIFYING - DRIVERS\n")

for driver in sorted(
    drivers,
    key=lambda d: d["driver_number"]
):
    print(
        f'{driver["driver_number"]:>2} | '
        f'{driver["name_acronym"]} | '
        f'{driver["full_name"]} | '
        f'{driver["team_name"]}'
    )
