#Step 1 Import all required modules
from airflow import DAG
from airflow.models import Variable
from airflow.decorators import task
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

from datetime import timedelta
from datetime import datetime
import snowflake.connector
import requests
import pandas as pd
import numpy as np



#Connect to snowflake account

def return_snowflake_conn():
    # Initialize the SnowflakeHook
    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn')

    # Execute the query and fetch results
    conn = hook.get_conn()
    return conn.cursor()

#Step to get data from Source

@task
def return_last_90d_price(symbol):
  """
   - return the last 90 days of the stock prices of symbol as a list of json strings
  """
  results = []   # empyt list for now to hold the 90 days of stock info (open, high, low, close, volume)
  vantage_api_key = Variable.get('apikey')
  for i in symbol:
           url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={i}&apikey={vantage_api_key}'
           r = requests.get(url)
           data = r.json()
           symbol_value = data["Meta Data"]["2. Symbol"]
           # Get today's date and the date 90 days ago
           today = datetime.now().date()
           start_date = today - timedelta(days=90)
           for d in data.get("Time Series (Daily)", {}):   # here d is a date: "YYYY-MM-DD"
                 stock_info = data["Time Series (Daily)"][d]
                 date = datetime.strptime(d, "%Y-%m-%d").date()
                 if start_date <= date <= today:  # Filter for the last 90 days
                      stock_info["date"] = d
                      stock_info["symbol"] = i
                      results.append(stock_info)
  return results


#Incremental Load
# Creating the table and and loading the data again
#Step1:- Load the data in Staging table.
#Step2:- Using the stageing table insert the records if not exist or update if any data changed for that records.

@task
def create_load_incremental(records):
    staging_table = "dev.stock.stock_price_stage"
    target_table = "dev.stock.stock_price_analysis"
    conn = return_snowflake_conn()
    try:
       conn.execute(f"""
               CREATE TABLE IF NOT EXISTS {target_table} (
                   date DATE PRIMARY KEY NOT NULL,
                   open DECIMAL(10, 2) NOT NULL,
                   high DECIMAL(10, 2) NOT NULL,
                   low DECIMAL(10, 2) NOT NULL,
                   close DECIMAL(10, 2) NOT NULL,
                   volume BIGINT NOT NULL,
                   symbol VARCHAR(10) NOT NULL
                         );
                         """)
          ## Create or replace the staging table
       conn.execute(f"""
             CREATE OR REPLACE TABLE {staging_table} (
                   date DATE  PRIMARY KEY NOT NULL,
                   open DECIMAL(10, 2) NOT NULL,
                   high DECIMAL(10, 2) NOT NULL,
                   low DECIMAL(10, 2) NOT NULL,
                   close DECIMAL(10, 2) NOT NULL,
                   volume BIGINT NOT NULL,
                   symbol VARCHAR(10) NOT NULL
                           );
                         """)

          # Insert records into the staging table
       for r in records:
              open = r["1. open"]
              high = r["2. high"]
              low = r["3. low"]
              close = r["4. close"]
              volume = r["5. volume"]
              date=r['date']
              symbol=r['symbol']
              insert_sql = f"INSERT INTO {staging_table} (date, open, high, low, close, volume, symbol) VALUES ('{date}',{open}, {high}, {low}, {close}, {volume}, '{symbol}')"
              conn.execute(insert_sql) # Execute within the with block

       conn.execute("COMMIT;")  

        # perform UPSERT
       upsert_sql = f"""
            MERGE INTO {target_table} AS target
            USING {staging_table} AS stage
            ON target.date = stage.date
               and target.symbol = stage.symbol
            WHEN MATCHED THEN
                UPDATE SET
                    target.date = stage.date,
                    target.open = stage.open,
                    target.high = stage.high,
                    target.low = stage.low,
                    target.close = stage.close,
                    target.volume = stage.volume,
                    target.symbol = stage.symbol
            WHEN NOT MATCHED THEN
                INSERT (date, open, high, low, close, volume, symbol)
                VALUES (stage.date,stage.open, stage.high, stage.low, stage.close, stage.volume, stage.symbol)
                 """

       conn.execute(upsert_sql)
       #Commit the change
       conn.execute("COMMIT;")  
       print(f"Stage Table {staging_table}, Target table create '{target_table}', Data loaded successfully in both the tables using Incremental Load ")
    except Exception as e:
        conn.execute("ROLLBACK;")
        print(e)
        raise e



with DAG(
    dag_id = 'Pipeline_STOCK_ETL',
    start_date = datetime(2024,11,10),
    catchup=False,
    tags=['ETL'],
    schedule = '@daily'
) as dag1:
    
    price_list = return_last_90d_price(["SBUX","NYT"])

    trigger_pipeline_continuation = TriggerDagRunOperator(
        task_id='trigger_pipeline_continuation',
        trigger_dag_id='BuildELT_dbt',  # Second DAG id
        wait_for_completion=True  # Set to True if you want the first DAG to wait for the second DAG's completion
    )

    create_load_incremental(price_list)>>trigger_pipeline_continuation

    

