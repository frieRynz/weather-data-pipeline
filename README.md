# Weather-data-pipeline
<p align="center">
  <img src="img\Screenshot 2026-08-30 225620.png" alt="Weather pipeline dashboard" width="400" height = "550">
</p>

## Setup & Running the Pipeline

### Prerequisites
- Python 3.10+
- Docker (for the PostgreSQL database)

### 1) Start the PostgreSQL database
```bash
docker-compose up -d db
```
The database listens on port **5433** (mapped from 5432) with persistent storage in a docker volume. Adminer (DB UI) is also available at http://localhost:8080 if you start the `adminer` service too.

### 2) Create your own credentials
Credentials are **not** committed to this repo — you need to create the two config files yourself:

**a. Database connection** — create a `.env` file in the project root (used by the pipeline scripts and `docker-compose.yml`):
```env
# values used by docker-compose.yml to bootstrap the database
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=weather_db

# values used by the pipeline scripts (script/load.py) to connect
DB_HOST=localhost
DB_PORT=5433
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=weather_db
```

**b. Streamlit app** — copy `app/.streamlit/secrets.toml.example` to `app/.streamlit/secrets.toml` and fill in the same database credentials (this file is gitignored, so it must be created manually).

### 3) Create the schema
Apply `sql/schema.sql` once (via Adminer at http://localhost:8080) OR:
```bash
docker exec -i weather_postgres psql -U your_db_user -d weather_db < sql/schema.sql
```

### 4) Install dependencies & run the pipeline
```bash
python -m venv venv
venv\Scripts\activate          # Windows (source venv/bin/activate on Linux/macOS)
pip install -r requirements.txt

python script/run_pipeline.py  # runs extract -> transform -> load
```
The pipeline is **idempotent** — run it as many times as you like; existing rows are updated via `ON CONFLICT DO UPDATE`, never duplicated. Each run's progress and row counts are logged to `logs/pipeline.log`.

### 5) Run the dashboard
```bash
streamlit run app/main.py
```


## 1) How you designed the schema and why (why you split or did not split tables, what keys you chose)
Before I started designing the schema, I first looked at what are being asked for in the SQL part of this assignment, which are temperature and chance of having rain. 
Knowing that, I went researching on open-meteo API document to find out how to get those information. After I have found it, I started to call for API request to see the raw JSON payload and found that the payload offers both city demographic; coordinates and time zone, and weather forecasts data; timestamp, temperature, and precipitation probability. 

After I had done observing on the payload, I tried to simulate the data flow for in and out throughout the pipeline and came up with an idea of splitting the data into 2 tables; city table (Strong entity) to store the city demographic information with city_id as the primary key and forecast table (Weak entity) to store the forecast data with (city_id, forecast_time) as the primary key. With this schema design, it ensures the most up-to-date the forecast data and prevent data redundancy by checking for city and forecast table's primary key with `ON CONFLICT DO UPDATE`.

## 2) How you made the pipeline idempotent
I made the pipeline idempotent by adding `ON CONFLICT DO UPDATE` to the insertion statement to ensure that if the inserted records happen to share the same set of primary key values to the existing ones inside the database, pipeline has to update that existing records' value(s) instead of adding new records to the database. 

## 3) What data issues you hit from the API and how you handled them
After completing the pipeline scripts, loading them to the database, and connecting those data to the Streamlit app, I discovered something unusual about the displayed hourly temperatures. The comparison metric is 7 hours shifted from the actual Thai user perspective. For example, the forecasted temperature, from the JSON payload, at midnight on the 29th is 27.8°C, which is actually the temperature at 7 AM Bangkok time. This was due to the default timezone Open-meteo provides, GMT, when the timezone parameter is not configured in the API request. Knowing that, I quickly added the time zone parameter to the extract.py, truncated the forecast table since all of its timestamps were in GMT, and re-ran the whole pipeline again to force the data timestamps to match with the Thai timezone. Additionally, since the `forecast` table uses `NOT NULL` constraints on the weather columns, the transform stage drops any hourly row containing a null temperature or precipitation probability (logged as a warning) so that a single bad value from the API can never crash the load or leave partial data behind.  

## 4) What you would change if this had to run every hour, all year
If this pipeline had to run 24/7 for a year, the very first thing I would like to change is the pipeline execution's method from manual to automated by employing the orchestrator tools like Apache Airflow or a more lightweight tool like Prefect, which also offer automatic retries and a notification system that could notify the data engineers of unexpected events when no one is looking at the log. 

Lastly, to ensure that no corrupted data enters the database for hours without anyone noticing, I would add validation tests to the transform stage for something like row-count sanity (e.g., ~168 hourly rows per city) and null-rate thresholds. On pass, the cleaned files are replaced as today; on failure, the run aborts before anything reaches the database. 

## 5) One or two interesting insights from the data
I have found 2 interesting insights while I was completing this assignment. 

__1. The coastal city shows the widest temperature range__: After solving the second query of the SQL part, I found out that Hat Yai, which is the coastal city, has the widest temperature range: 12.5°C, versus 8.2 (Phuket), 7.7 (Bangkok), 7.3 (Khon Kaen), and 6.3 (Chiang Mai). The reason is likely because of the sea-breeze convection. During the day, the land heats faster than the sea, moist air flows inland and rises, and this builds heavy afternoon rain clouds. Those clouds also block sunlight, dragging the daily maximum down from 36.0°C (Sep 1) to 29.2°C (Sep 3), which is about 7°C in two days, before temperatures slowly recover (32.8°C on Sep 4) as the rain chance fades.

__2. A rainy spell clearly breaks the heat in Hat Yai__:
<table>
  <tr>
    <td width="330" valign="top">
      <img src="img\image.png" alt="Hat Yai daily temperature vs precipitation probability" width="310">
    </td>
    <td valign="top">
      While I was looking at Hat Yai forecast dashboard, I saw a clear temperature drop: the daily maximum falls from 36.0°C (Sep 1) to 29.2°C (Sep 3), which is about 7°C in two days. Seeing that, I went to query the precipitation probability in the same duration and found that this happens exactly when the rain chance goes up: precipitation_prob peaks at 100% (Sep 2) and 85% (Sep 3), with 9 and 5 hours at ≥50% chance, while Aug 30 had no such hours at all. Sep 1 is interesting because it is both the hottest day <em>and</em> the day the rain starts building (7 rain-likely hours). After the rain, the temperature comes back slowly (32.8°C on Sep 4) as the rain chance goes down. This pattern matches what clouds do: they block the sun and stop the day from heating up to 35°C+. (Evidence: daily average of <code>temperature_2m</code> compared with <code>precipitation_probability</code>, when one goes up, the other goes down.)
    </td>
  </tr>
</table>

## 6) Which parts you used AI tools for
I used AI to help me complete this assignment in almost every part. Let me break them down how: 
1. __Ingestion script__: I used AI to help me validate my pipeline workflow that I planned, debug ETL scripts errors, write the logger helper script, and improve the pipeline scripts to cover all criteria of assignment instruction. 
2. __SQL__ : I used AI  to validate whether the sql queries I wrote really satisfy the SQL questions or not. 
3. __Display__: I used AI for brainstorming and to help me debug the streamlit script. 
4. __README summary__: I used AI to help formatting the images and grammar checks. 