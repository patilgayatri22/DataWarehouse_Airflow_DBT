from airflow.decorators import task
from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import get_current_context
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

from datetime import datetime
from datetime import timedelta
import logging
import snowflake.connector


def return_snowflake_conn():

    # Initialize the SnowflakeHook
    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn')

    # Execute the query and fetch results
    conn = hook.get_conn()
    return conn.cursor()


@task
def run_ctas(primary_key=None):

    table = "dev.analytics.session_summary"
    select_sql = """SELECT u.*, s.ts
    FROM dev.raw_data.user_session_channel u
    JOIN dev.raw_data.session_timestamp s ON u.sessionId=s.sessionId
    """

    logging.info(table)
    logging.info(select_sql)

    cur = return_snowflake_conn()

    try:
        cur.execute("BEGIN;")
        sql = f"CREATE OR REPLACE TABLE {table} AS {select_sql}"
        logging.info(sql)
        cur.execute(sql)

        # do primary key uniquess check
        if primary_key is not None:
            sql = f"SELECT {primary_key}, COUNT(1) AS cnt FROM {table} GROUP BY 1 ORDER BY 2 DESC LIMIT 1"
            print(sql)
            cur.execute(sql)
            result = cur.fetchone()
            print(result, result[1])
            if int(result[1]) > 1:
                print("!!!!!!!!!!!!!!")
                raise Exception(f"Primary key uniqueness failed: {result}")
            
        cur.execute("COMMIT;")
    except Exception as e:
        cur.execute("ROLLBACK")
        logging.error('Failed to sql. Completed ROLLBACK!')
        raise


with DAG(
    dag_id = 'BuildELT_CTAS',
    start_date = datetime(2024,10,24),
    catchup=False,
    tags=['ELT'],
    schedule = '45 2 * * *'
) as dag:

    

    run_ctas(table, select_sql, primary_key='sessionId')
