import os 
import json
import time

from logger import setup_logger

logger = setup_logger("transform")

script_dir = os.path.dirname(os.path.abspath(__file__))
raw_data_dir = os.path.abspath(os.path.join(script_dir, '..', 'data', 'raw_data'))

start_time = time.time()
logger.info("Transformation started")

city_data = []
forecast_data  = []

files_processed = 0

for filename in os.listdir(raw_data_dir):
    if filename.endswith(".json"):
        file_path = os.path.join(raw_data_dir, filename)
        
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            city_name = filename.replace("_7days_hourly_weather.json", "")
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
            for t, tm, pcp in zip(time_list, temp_2m, precip_prob):
                forecast_dict = {
                    "city_name": city_name,
                    "forecast_time": t,
                    "temperature": tm,
                    "precipitation_prob": pcp
                }
                forecast_data.append(forecast_dict)
            
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
print(f"Transformation complete: {files_processed} files -> {len(city_data)} cities, "
      f"{len(forecast_data)} forecast rows. See logs/pipeline.log for details.")
