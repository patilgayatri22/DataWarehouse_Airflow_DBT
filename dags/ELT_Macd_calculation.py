from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from airflow.hooks.base import BaseHook

conn = BaseHook.get_connection('snowflake_conn')

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 11, 10),  # Set your start date,
}

# Define the DAG
dag = DAG(
    'dbt_airflow_dag',
    default_args=default_args,
    description='DAG to run dbt commands (run, test, snapshot)',
    schedule=None,  # This will run once a day
    catchup=False,
)

# Task to run dbt commands (dbt run)
run_dbt = BashOperator(
    task_id='dbt_run',
    bash_command='cd "/Users/gayatripatil/Documents/airflow/sjsu-data226/build_lab2" && dbt run',
    dag=dag,
)

# Task to run dbt tests (dbt test)
run_dbt_test = BashOperator(
    task_id='dbt_test',
    bash_command='cd "/Users/gayatripatil/Documents/airflow/sjsu-data226/build_lab2" && dbt test',
    dag=dag,
)

# Task to run dbt snapshot (dbt snapshot)
run_dbt_snapshot = BashOperator(
    task_id='dbt_snapshot',
    bash_command='cd "/Users/gayatripatil/Documents/airflow/sjsu-data226/build_lab2" && dbt snapshot',
    dag=dag,
)

# Set task dependencies (order of execution)
run_dbt >> run_dbt_test >> run_dbt_snapshot
