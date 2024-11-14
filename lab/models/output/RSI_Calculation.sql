WITH PriceChanges AS (
    SELECT
        date,
        symbol,
        close,
        LEAD(close) OVER (PARTITION BY symbol ORDER BY date) AS next_close
    FROM
        {{ source('stock', 'stock_price_analysis') }}  -- Replace 'stock' and 'stock_price_analysis' with your actual source name and table
),
PriceGainsLosses AS (
    SELECT
        date,
        symbol,
        close,
        next_close,
        CASE 
            WHEN next_close > close THEN next_close - close
            ELSE 0 
        END AS gain,
        CASE 
            WHEN next_close < close THEN close - next_close
            ELSE 0 
        END AS loss
    FROM
        PriceChanges
),
AverageGainsLosses AS (
    SELECT
        date,
        symbol,
        AVG(gain) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS avg_gain,
        AVG(loss) OVER (PARTITION BY symbol ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS avg_loss
    FROM
        PriceGainsLosses
),
RSI_Calculation AS (
    SELECT
        date,
        symbol,
        avg_gain,
        avg_loss,
        CASE 
            WHEN avg_loss = 0 THEN 100
            ELSE 100 - (100 / (1 + (avg_gain / avg_loss)))
        END AS rsi
    FROM
        AverageGainsLosses
)
SELECT 
    date, 
    symbol, 
    rsi
FROM 
    RSI_Calculation
WHERE
    date >= (SELECT MIN(date) FROM {{ source('stock', 'stock_price_analysis') }}) + INTERVAL '14 DAY'
ORDER BY
    symbol, date
