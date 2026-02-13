import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/usr/local/airflow/dbt_project")
DBT_PROFILES_DIR = os.environ.get("DBT_PROFILES_DIR", DBT_PROJECT_DIR)
DBT_PROFILE_NAME = os.environ.get("DBT_PROFILE_NAME", "affle_shop")

with DAG(
    dag_id="dbt_wap_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["dbt", "wap"],
) as dag:

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"dbt deps --profiles-dir {DBT_PROFILES_DIR} --profile {DBT_PROFILE_NAME}"
        ),
    )

    dbt_build_fact_visits_and_upstream = BashOperator(
        task_id="dbt_build_fact_visits_and_upstream",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"dbt build --profiles-dir {DBT_PROFILES_DIR} --profile {DBT_PROFILE_NAME} "
            f"-s +fact_visits"
        ),
    )

    dbt_deps >> dbt_build_fact_visits_and_upstream
