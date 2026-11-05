# Formula 1 Telemetry Analysis with Python & FastF1

A command-line tool that fetches official Formula 1 timing and sensor data via the **FastF1** API to compare driver telemetry across any Grand Prix session.

![Sample Telemetry Comparison](sample_telemetry_comparison.png)

## Features
- **Multi-Channel Telemetry**: Compares Speed (km/h), Throttle (%), Brake application, and Gear shifts over track distance.
- **Circuit Corner Annotations**: Automatically plots vertical reference markers for every corner on the circuit.
- **Official Team Styling**: Uses FastF1 dynamic color mapping to match driver traces to their official team liveries (with automatic high-contrast dashed differentiation for teammates).
- **Smart Local Caching**: Caches session data locally in `f1_cache/` so repeat analyses run in seconds.

## Installation

1. Clone or extract this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/f1-telemetry-analyzer.git
   cd f1-telemetry-analyzer
   ```

2. Create a virtual environment (optional but recommended) and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run with default parameters (2024 Monza Qualifying: Leclerc vs. Piastri):
```bash
python analyze_telemetry.py
```

Or pass custom CLI arguments for any race, session, or driver pairing:
```bash
python analyze_telemetry.py --year 2024 --gp Silverstone --session Q --d1 HAM --d2 VER --out silverstone_q.png
```

### CLI Options
| Flag | Default | Description |
| :--- | :--- | :--- |
| `--year` | `2024` | Championship season year (e.g., `2023`, `2024`, `2025`) |
| `--gp` | `Monza` | Grand Prix name, location, or round number |
| `--session` | `Q` | Session code (`FP1`, `FP2`, `FP3`, `Q`, `S`, `R`) |
| `--d1` | `LEC` | 3-letter FIA driver identifier for Driver 1 |
| `--d2` | `PIA` | 3-letter FIA driver identifier for Driver 2 |
| `--out` | `telemetry_comparison.png` | Output PNG filename |
