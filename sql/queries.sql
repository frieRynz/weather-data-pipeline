-- 1) avg, max, and min temp per city per day
SELECT c.city_name as city,
       date(f.forecast_time) as day,
       round(avg(f.temperature),2) as average_temperature,
       max(f.temperature) as maximum_temperature,
       min(f.temperature) as minimum_temperature
from forecast f
INNER JOIN city c
on f.city_id = c.city_id
group by c.city_name, day
ORDER BY c.city_name, day; 

-- 2 which city has highest (max - min) / temp range
SELECT c.city_name,(max(f.temperature) - min(f.temperature)) as temp_range
FROM forecast f INNER JOIN city c ON f.city_id = c.city_id 
GROUP BY c.city_name
ORDER BY temp_range desc
limit 1;

-- 3 The hour with the highest chance of rain per city, per day
with ranked_rain as 
   (select c.city_name, 
    date(f.forecast_time) as day, 
    extract(hour from f.forecast_time)as hour, 
    f.precipitation_prob,
    ROW_NUMBER() over(
         partition by c.city_name, date(f.forecast_time)
         ORDER BY f.precipitation_prob DESC
        ) as daily_rank
    from forecast f
    INNER JOIN city c ON c.city_id = f.city_id
   )

select city_name, day, hour, precipitation_prob 
from ranked_rain
where daily_rank = 1;

-- 4 For each city, the diff. in daily average temperature compared to the previous day 
WITH daily_avgTemp AS (
    SELECT c.city_name,
           date(f.forecast_time) AS day,
           round(avg(f.temperature), 2) AS avg_temp
    FROM forecast f
    INNER JOIN city c ON f.city_id = c.city_id
    GROUP BY c.city_name, day
)

SELECT city_name,
       day,
       avg_temp AS today_average_temp,
       abs(avg_temp - LAG(avg_temp,1) OVER (PARTITION BY city_name ORDER BY day))
           AS temp_diff_from_yesterday
FROM daily_avgTemp
ORDER BY city_name, day;
