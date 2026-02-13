from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# ------------------------------------------------------------------------------
# YouTube Capstone dbt Pipeline (Astro / Airflow)
#
# Runs:
#   dbt deps -> dbt seed -> dbt run -> dbt test
#
# Ensures dbt uses the correct project + profiles paths inside the Astro container
# and passes required env vars (SNOWFLAKE_*, DBT_*, STUDENT_SCHEMA).
# ------------------------------------------------------------------------------

DBT_PROFILE_NAME = "youtube_analytics_capstone"

# Inside the Astro container, the repo is mounted at /usr/local/airflow
DBT_PROJECT_PATH = "/usr/local/airflow/include/youtube_capstone/transform/youtube_analytics"
DBT_PROFILES_PATH = DBT_PROJECT_PATH  # profiles.yml lives in the same folder

BASE_DBT_ENV = {
    "DBT_PROFILE_NAME": DBT_PROFILE_NAME,
    "DBT_PROFILES_DIR": DBT_PROFILES_PATH,
    "DBT_PROJECT_DIR": DBT_PROJECT_PATH,
    "DBT_LOG_FORMAT": "text",
    "DBT_PACKAGES_INSTALL_PATH": "/tmp/dbt_packages",
    "DBT_TARGET_PATH": "/tmp/dbt_target",
}

# Pass through Snowflake + dbt env vars AND STUDENT_SCHEMA (required by your project)
PASSTHROUGH_ENV = {
    k: v
    for k, v in os.environ.items()
    if k.startswith("SNOWFLAKE_") or k.startswith("DBT_") or k == "STUDENT_SCHEMA"
}

DBT_ENV = {**BASE_DBT_ENV, **PASSTHROUGH_ENV}

default_args = {
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="youtube_capstone_dbt",
    start_date=datetime(2026, 1, 1),
    schedule=None,  # manual trigger for submission
    catchup=False,
    default_args=default_args,
    tags=["youtube", "capstone", "dbt"],
) as dag:
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        cwd=DBT_PROJECT_PATH,
        env=DBT_ENV,
        bash_command="dbt deps",
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        cwd=DBT_PROJECT_PATH,
        env=DBT_ENV,
        bash_command="dbt seed",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        cwd=DBT_PROJECT_PATH,
        env=DBT_ENV,
        bash_command="dbt run",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        cwd=DBT_PROJECT_PATH,
        env=DBT_ENV,
        bash_command="dbt test",
    )

    dbt_deps >> dbt_seed >> dbt_run >> dbt_test