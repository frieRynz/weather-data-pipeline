CREATE TABLE IF NOT EXISTS city(
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(50) UNIQUE NOT NULL,
    latitude NUMERIC NOT NULL,
    longitude NUMERIC NOT NULL,
    timezone VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS forecast(
    city_id INTEGER REFERENCES city(city_id),
    forecast_time TIMESTAMP NOT NULL, 
    temperature NUMERIC NOT NULL, 
    precipitation_prob INTEGER NOT NULL,
    PRIMARY KEY (city_id, forecast_time)
);