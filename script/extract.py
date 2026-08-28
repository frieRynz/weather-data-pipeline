import requests 
import json
import os

weather_url = f"https://api.open-meteo.com/v1/forecast"

location = {'Bangkok': [13.7540,100.5014],
            'Chiang Mai': [18.7904, 98.9847],
            'Phuket': [7.8906, 98.3981],
            'Khon Kaen': [16.4467, 102.8330],
            'Hat Yai': [7.0084, 100.4767]}

params = {
    "hourly": ["temperature_2m", "precipitation_probability"],
    "latitude" : 13.7540,
    "longitude" : 100.5014
}

# 1. Get the absolute path of the folder containing extract.py (the 'script' folder)
script_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Go up one level to the project root, then point to data/raw_data
raw_data_dir = os.path.abspath(os.path.join(script_dir, "..", "data", "raw_data"))

for city, coordinates in location.items():
    latitude = coordinates[0]
    longitude = coordinates[1]
    
    city_params = params.copy()
    city_params["latitude"] = latitude
    city_params["longitude"] = longitude    
    
    response = requests.get(weather_url, params=city_params)
    
    if response.status_code == 200: 
        weather_data = response.json()
        
        os.makedirs(raw_data_dir, exist_ok=True)
        file_path = os.path.join(raw_data_dir, f"{city}_7days_hourly_weather.json")
        
        with open(file_path, 'w') as f:
            json.dump(weather_data, f, indent=2)