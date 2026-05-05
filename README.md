# PowGenAUS: Interactive Power Generation Dashboard for Australia

PowGenAUS is an interactive Streamlit dashboard for exploring power generation and power station capacity across Australia. The application combines tabular power plant data with Australian state boundaries to support spatial exploration through maps, charts, indicators, filters and downloadable data tables.

This enhanced version is suitable for an MSc Applied Geoinformatics ePortfolio because it demonstrates practical software development, geospatial data processing, interactive WebGIS design and data visualisation.

## Main Features

- Interactive Streamlit dashboard
- Sidebar filters for year, fuel type, state, minimum capacity and station/owner search
- Choropleth map showing total installed capacity or reported generation by Australian state
- Optional clustered markers for individual power stations
- Marker popups with station name, owner, state, fuel type, capacity and generation
- Overview indicators for number of stations, capacity, generation and fuel/state count
- Top 10 power stations by capacity
- Fuel type summary table
- Interactive Plotly charts:
  - capacity by fuel type
  - generation by fuel type
  - state-level comparison
  - capacity vs generation scatter plot
  - filtered yearly generation trend
- Data inspection tabs
- CSV download buttons for filtered stations, state summary, fuel summary and raw Australia records
- Cleaner project structure and updated requirements

## Project Structure

```text
PowGenAUS_enhanced/
│
├── code/
│   ├── main.py              # Main Streamlit application
│   ├── dashboard.py         # Dashboard, charts and map components
│   ├── preprocess.py        # Data loading, cleaning, spatial join and aggregation
│   ├── requirements.txt     # Python pip dependencies
│   └── environment.yml      # Optional Conda environment file
│
├── data/
│   ├── global_power_plant_database.csv
│   └── AustralianStates.geojson
│
├── portfolio_project_text.md
├── README.md
└── LICENSE
```

## How to Run the Application

### Option 1: Run with pip and venv

1. Open the project folder in VS Code, Command Prompt, PowerShell or Terminal.

2. Create a virtual environment:

```bash
python -m venv .venv
```

3. Activate the virtual environment.

On Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

On Windows Command Prompt:

```bash
.venv\Scripts\activate.bat
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

4. Install the required packages:

```bash
pip install -r code/requirements.txt
```

5. Run the dashboard from the project root folder:

```bash
streamlit run code/main.py
```

6. Streamlit will open the app in your browser. If it does not open automatically, copy the local URL shown in the terminal, usually:

```text
http://localhost:8501
```

### Option 2: Run with Conda

1. Open a terminal in the project folder.

2. Create the environment:

```bash
conda env create -f code/environment.yml
```

3. Activate it:

```bash
conda activate powgenaus
```

4. Run the app:

```bash
streamlit run code/main.py
```

## Data

The dashboard uses the Global Power Plant Database filtered to Australian power stations and combines it with Australian state boundary GeoJSON data. The source dataset in this project contains reported generation values for selected years and should be treated as a demonstration dataset for academic software development.
