CREATE TABLE IF NOT EXISTS weather_forecasts (
    id BIGSERIAL PRIMARY KEY,
    forecast_at TIMESTAMPTZ NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(10, 6) NOT NULL,
    temperature_c NUMERIC(5, 2) NOT NULL,
    relative_humidity_pct SMALLINT NOT NULL,
    precipitation_mm NUMERIC(8, 2) NOT NULL,
    wind_speed_kmh NUMERIC(7, 2) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_weather_forecasts_location_time
        UNIQUE (latitude, longitude, forecast_at),

    CONSTRAINT chk_weather_forecasts_relative_humidity_pct
        CHECK (relative_humidity_pct >= 0 AND relative_humidity_pct <= 100),

    CONSTRAINT chk_weather_forecasts_precipitation_mm
        CHECK (precipitation_mm >= 0),

    CONSTRAINT chk_weather_forecasts_wind_speed_kmh
        CHECK (wind_speed_kmh >= 0)
);
