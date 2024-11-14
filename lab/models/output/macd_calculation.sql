WITH stock_data AS (
    SELECT 
        SYMBOL,
        DATE,
        CLOSE,
        ROW_NUMBER() OVER (PARTITION BY SYMBOL ORDER BY DATE) AS rn
    FROM {{ ref('stock_price_analysis') }}  -- Replace with the reference to your actual source table in DBT
),

-- Calculate 12-day EMA
ema_12 AS (
    SELECT
        SYMBOL,
        DATE,
        CLOSE AS EMA_12,
        rn
    FROM stock_data
    WHERE rn = 1

    UNION ALL

    SELECT 
        sd.SYMBOL,
        sd.DATE,
        (sd.CLOSE * (2.0 / (12 + 1))) + (e.EMA_12 * (1 - (2.0 / (12 + 1)))) AS EMA_12,
        sd.rn
    FROM stock_data sd
    JOIN ema_12 e ON sd.SYMBOL = e.SYMBOL AND sd.rn = e.rn + 1
),

-- Calculate 26-day EMA
ema_26 AS (
    SELECT 
        SYMBOL,
        DATE,
        CLOSE AS EMA_26,
        rn
    FROM stock_data
    WHERE rn = 1

    UNION ALL

    SELECT 
        sd.SYMBOL,
        sd.DATE,
        (sd.CLOSE * (2.0 / (26 + 1))) + (e.EMA_26 * (1 - (2.0 / (26 + 1)))) AS EMA_26,
        sd.rn
    FROM stock_data sd
    JOIN ema_26 e ON sd.SYMBOL = e.SYMBOL AND sd.rn = e.rn + 1
),

-- Calculate MACD by subtracting 26-day EMA from 12-day EMA
macd_calculation AS (
    SELECT 
        e12.SYMBOL,
        e12.DATE,
        e12.EMA_12 - e26.EMA_26 AS MACD,
        e12.rn
    FROM ema_12 e12
    JOIN ema_26 e26 ON e12.SYMBOL = e26.SYMBOL AND e12.DATE = e26.DATE
),

-- Calculate 9-day EMA of MACD as Signal Line
signal_line AS (
    SELECT 
        SYMBOL,
        DATE,
        MACD,
        MACD AS Signal,
        rn
    FROM macd_calculation
    WHERE rn = 1

    UNION ALL

    SELECT 
        mc.SYMBOL,
        mc.DATE,
        mc.MACD,
        (mc.MACD * (2.0 / (9 + 1))) + (sl.Signal * (1 - (2.0 / (9 + 1)))) AS Signal,
        mc.rn
    FROM macd_calculation mc
    JOIN signal_line sl ON mc.SYMBOL = sl.SYMBOL AND mc.rn = sl.rn + 1
)

-- Final output
SELECT 
    SYMBOL,
    DATE,
    MACD,
    Signal,
    MACD - Signal AS Histogram
FROM signal_line
ORDER BY SYMBOL, DATE
