import os
import json
import time
from dotenv import load_dotenv
import psycopg2
from psycopg2 import Error
from psycopg2.extras import execute_values

from logger import setup_logger

logger = setup_logger("load")

script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "..", ".env"))

clean_dir = os.path.abspath(os.path.join(script_dir, "..", "data","cleaned_data"))

start_time = time.time()
logger.info("Load started")

cities = {}
forecasts = {}

with open(os.path.join(clean_dir, "cleaned_cities.json"), "r", encoding="utf-8") as f: 
    cities = json.load(f)
    
with open(os.path.join(clean_dir, "cleaned_forecasts.json"), "r", encoding="utf-8") as f: 
    forecasts = json.load(f)    

logger.info(f"Loaded cleaned data: {len(cities)} cities, {len(forecasts)} forecast records")
    
try:
    connection = psycopg2.connect(
        host = os.getenv("DB_HOST"),
        database = os.getenv("DB_NAME"),
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        port = os.getenv("DB_PORT")
    )
    
    cursor = connection.cursor()
    
    city_rows = []
    for c in cities: 
        row = (c["city_name"], c["latitude"], c["longitude"], c["timezone"])
        city_rows.append(row)
        
    execute_values(cursor, """
        INSERT INTO city (city_name, latitude, longitude, timezone)
        VALUES %s
        ON CONFLICT (city_name) DO UPDATE SET
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            timezone = EXCLUDED.timezone;
    """, city_rows)
    logger.info(f"Upserted {len(city_rows)} city row(s)")
    
    cursor.execute("SELECT city_name, city_id FROM city;")
    db_cities = cursor.fetchall()
    
    city_map = {}
    for row in db_cities:
        city_map[row[0]] = row[1]
        # 'Bangkok' : 1
    
    forecast_row = []
    skipped = []
    for f in forecasts:
        c_id = city_map.get(f["city_name"]) # city_map['Bangkok'] = 1
        if c_id is None:
            skipped.append(f["city_name"])
            continue
        
        row = (c_id, f["forecast_time"], f["temperature"], f["precipitation_prob"])
        forecast_row.append(row)
    
    if skipped:
        logger.warning(f"Skipped {len(skipped)} forecast record(s) for unknown cities: {set(skipped)}")
       
    execute_values(cursor, """
        INSERT INTO forecast (city_id, forecast_time, temperature, precipitation_prob)
        VALUES %s
        ON CONFLICT (city_id, forecast_time)
        DO UPDATE SET
        temperature = EXCLUDED.temperature,
        precipitation_prob = EXCLUDED.precipitation_prob;
        """, forecast_row)
    logger.info(f"Upserted {len(forecast_row)} forecast row(s)")
    
    connection.commit()
    duration = time.time() - start_time
    logger.info(f"Load complete in {round(duration, 2)} seconds: "
                f"{len(city_rows)} cities, {len(forecast_row)} forecast rows committed to PostgreSQL")
    print(f"Load complete: {len(city_rows)} cities, {len(forecast_row)} forecast rows committed "
          f"in {round(duration, 2)}s. See logs/pipeline.log for details.")
    
except (Exception, Error) as error:
    logger.error(f"Load failed: {error}")
    if 'connection' in locals() and connection:
        connection.rollback()
        logger.info("Transaction rolled back — no partial data was saved")

finally:
    if 'connection' in locals() and cursor:
        cursor.close()
    if 'connection' in locals() and connection:
        connection.close()
        logger.info("PostgreSQL connection is closed")