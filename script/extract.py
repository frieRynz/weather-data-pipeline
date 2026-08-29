import requests 
import json
import os
import time

from logger import setup_logger

logger = setup_logger("extract")

weather_url = f"https://api.open-meteo.com/v1/forecast"

location = {'Bangkok': [13.7540,100.5014],
            'Chiang Mai': [18.7904, 98.9847],
            'Phuket': [7.8906, 98.3981],
            'Khon Kaen': [16.4467, 102.8330],
            'Hat Yai': [7.0084, 100.4767]}

params = {
    "hourly": ["temperature_2m", "precipitation_probability"],
}

script_dir = os.path.dirname(os.path.abspath(__file__)) # 1. Get absolute path of the folder containing extract.py 

raw_data_dir = os.path.abspath(os.path.join(script_dir, "..", "data", "raw_data")) 

start_time = time.time()
logger.info("Extraction started")

successful_cities = 0
failed_cities = []
total_rows_fetched = 0

for city, coordinates in location.items():
    latitude = coordinates[0]
    longitude = coordinates[1]
    
    city_params = params.copy()
    city_params["latitude"] = latitude
    city_params["longitude"] = longitude    
    
    try:
        response = requests.get(weather_url, params=city_params, timeout=10)
        
        response.raise_for_status()
        
        weather_data = response.json()
        
        successful_cities+=1
        total_rows_fetched+= len(weather_data["hourly"]["time"])
                
        os.makedirs(raw_data_dir, exist_ok=True)
        file_path = os.path.join(raw_data_dir, f"{city}_7days_hourly_weather.json")
                
        with open(file_path, 'w') as f:
            json.dump(weather_data, f, indent=2)
            
        logger.info(f"Successfully fetched and saved {city} ({len(weather_data['hourly']['time'])} rows)")
        
    except Exception as e:
        logger.error(f"Failed to fetch {city}'s weather data. Error: {e}")
        failed_cities.append(city)
        
        
duration = time.time() - start_time

logger.info(f"Extraction Complete in {round(duration, 2)} seconds")
logger.info(f"{successful_cities} weather data have been extracted from Open-meteo")

if failed_cities:
    logger.error(f"{failed_cities} city(s) failed to be extracted")
    
logger.info(f"Total rows fetched: {total_rows_fetched}")
print(f"Extraction complete: {successful_cities} cities, {total_rows_fetched} rows "
      f"({len(failed_cities)} failed). See logs/pipeline.log for details.")