import os 
import json
import time

from logger import setup_logger

logger = setup_logger("transform")

script_dir = os.path.dirname(os.path.abspath(__file__))
raw_data_dir = os.path.abspath(os.path.join(script_dir, '..', 'data', 'raw_data'))

start_time = time.time()
logger.info("Transformation started")

# Read the extraction manifest so only cities fetched in the CURRENT run are
# transformed — stale raw JSON left behind by a failed city in a previous run
# must never reach the database.
manifest_path = os.path.join(raw_data_dir, "_manifest.json")
fetched_cities = None
if os.path.exists(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as mf:
        manifest = json.load(mf)
    fetched_cities = set(manifest.get("fetched_cities", []))
    logger.info(f"Extraction manifest loaded: cities fetched this run: {sorted(fetched_cities)}")
else:
    logger.warning("No extraction manifest found — processing all raw files "
                   "(run extract.py first for per-run freshness guarantees)")

city_data = []
forecast_data  = []

files_processed = 0
skipped_stale = []
dropped_null_rows = {}  # city_name -> count

for filename in os.listdir(raw_data_dir):
    if filename.endswith(".json") and filename != "_manifest.json":
        city_name = filename.replace("_7days_hourly_weather.json", "")

        # Failure atomicity: skip raw files not produced by the current run
        if fetched_cities is not None and city_name not in fetched_cities:
            logger.warning(f"{city_name}: skipped — raw file is stale (city was not "
                           f"successfully fetched in the current extraction run)")
            skipped_stale.append(city_name)
            continue

        file_path = os.path.join(raw_data_dir, filename)
        
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            files_processed += 1
            
            city_dict = {}
            city_dict["city_name"] = city_name
            city_dict["latitude"] = data["latitude"]
            city_dict["longitude"] = data["longitude"]
            city_dict["timezone"] = data["timezone"]
            city_data.append(city_dict)
            
            time_list = data["hourly"]["time"]
            temp_2m = data["hourly"]["temperature_2m"]
            precip_prob = data["hourly"]["precipitation_probability"]
            
            # Data quality checks — surface API data issues in the log
            if len(time_list) != len(temp_2m) or len(time_list) != len(precip_prob):
                logger.warning(
                    f"{city_name}: column length mismatch "
                    f"(time={len(time_list)}, temp={len(temp_2m)}, precip={len(precip_prob)})"
                )
            null_temps = temp_2m.count(None)
            if null_temps:
                logger.warning(f"{city_name}: {null_temps} null temperature value(s) found")
            null_precip = precip_prob.count(None)
            if null_precip:
                logger.warning(f"{city_name}: {null_precip} null precipitation value(s) found")
            
            rows_before = len(forecast_data)
            dropped_here = 0
            for t, tm, pcp in zip(time_list, temp_2m, precip_prob):
                # Null handling: drop rows with null temperature or precipitation
                # probability instead of loading them — the forecast table has
                # NOT NULL constraints, so a single null would crash the load.
                if tm is None or pcp is None:
                    dropped_here += 1
                    continue
                forecast_dict = {
                    "city_name": city_name,
                    "forecast_time": t,
                    "temperature": tm,
                    "precipitation_prob": pcp
                }
                forecast_data.append(forecast_dict)

            if dropped_here:
                dropped_null_rows[city_name] = dropped_here
                logger.warning(f"{city_name}: dropped {dropped_here} row(s) with null "
                               f"temperature/precipitation values (NOT NULL constraint protection)")
            
            logger.info(f"{city_name}: transformed {len(forecast_data) - rows_before} forecast rows")
            
if files_processed == 0:
    logger.error("No raw data files found — run extract.py first")

cleaned_data_dir = os.path.abspath(os.path.join(script_dir, '..', 'data', 'cleaned_data'))       
os.makedirs(cleaned_data_dir, exist_ok=True)

file_path1 = os.path.join(cleaned_data_dir, "cleaned_cities.json")
file_path2 = os.path.join(cleaned_data_dir, "cleaned_forecasts.json")


def write_json(path, payload):
    with open(path, "w") as f: 
        json.dump(payload, f, indent=2)
        
write_json(file_path1, city_data)
write_json(file_path2, forecast_data)

duration = time.time() - start_time
logger.info(
    f"Transformation complete in {round(duration, 2)} seconds: "
    f"{files_processed} raw file(s) -> {len(city_data)} cities, {len(forecast_data)} forecast rows"
)
if skipped_stale:
    logger.warning(f"{len(skipped_stale)} stale raw file(s) skipped: {skipped_stale}")
if dropped_null_rows:
    logger.warning(f"Dropped null-value row(s) per city: {dropped_null_rows}")
print(f"Transformation complete: {files_processed} files -> {len(city_data)} cities, "
      f"{len(forecast_data)} forecast rows. See logs/pipeline.log for details.")
