import os 
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
raw_data_dir = os.path.abspath(os.path.join(script_dir, '..', 'data', 'raw_data'))

city_data = []
forecast_data  = []

for filename in os.listdir(raw_data_dir):
    if filename.endswith(".json"):
        file_path = os.path.join(raw_data_dir, filename)
        
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            city_name = filename.replace("_7days_hourly_weather.json", "")
            
            city_dict = {}
            city_dict["city_name"] = city_name
            city_dict["latitude"] = data["latitude"]
            city_dict["longitude"] = data["longitude"]
            city_dict["timezone"] = data["timezone"]
            city_data.append(city_dict)
            
            
            time = data["hourly"]["time"]
            temp_2m = data["hourly"]["temperature_2m"]
            precip_prob = data["hourly"]["precipitation_probability"]
            
            for t, tm, pcp in zip(time, temp_2m, precip_prob):
                forecast_dict = {
                    "city_name": city_name,
                    "forecast_time":t,
                    "temparture":tm,
                    "precipitation_prob":pcp
                }
                forecast_data.append(forecast_dict)

cleaned_data_dir = os.path.abspath(os.path.join(script_dir, '..', 'data', 'cleaned_data'))       
os.makedirs(cleaned_data_dir, exist_ok=True)

file_path1 = os.path.join(cleaned_data_dir, "cleaned_cities.json")
file_path2 = os.path.join(cleaned_data_dir, "cleaned_forecasts.json")


def write_json(path, payload):
    with open(path, "w") as f: 
        json.dump(payload, f, indent=2)
        
write_json(file_path1, city_data)
write_json(file_path2, forecast_data)

# print(city_data, "\n")
# print(forecast_data)
