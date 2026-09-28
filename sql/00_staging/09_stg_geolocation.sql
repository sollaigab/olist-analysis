-- Source grain: 1 row = 1 geocoded point (1,000,163 rows for ~19k prefixes).
-- Joining that to customers would multiply every order by ~50.
-- Staging therefore collapses it to 1 row per zip prefix using the MEDIAN
-- coordinate, which resists the geocoding outliers that a mean would absorb.
-- City/state are taken as the most frequent spelling for the prefix.
CREATE OR REPLACE TABLE stg.geolocation AS
WITH typed AS (
    SELECT
        lpad(geolocation_zip_code_prefix, 5, '0') AS zip_prefix,
        TRY_CAST(geolocation_lat AS DOUBLE)       AS lat,
        TRY_CAST(geolocation_lng AS DOUBLE)       AS lng,
        lower(trim(geolocation_city))             AS city,
        upper(trim(geolocation_state))            AS state
    FROM raw.geolocation
),
ranked_place AS (
    SELECT zip_prefix, city, state,
           row_number() OVER (PARTITION BY zip_prefix ORDER BY count(*) DESC, city) AS rn
    FROM typed
    GROUP BY zip_prefix, city, state
)
SELECT
    t.zip_prefix,
    median(t.lat) AS lat,
    median(t.lng) AS lng,
    any_value(p.city)  AS city,
    any_value(p.state) AS state,
    count(*)           AS source_points
FROM typed t
JOIN ranked_place p ON p.zip_prefix = t.zip_prefix AND p.rn = 1
GROUP BY t.zip_prefix;
