import os
from datetime import datetime, timedelta

from airflow.decorators import dag
from airflow.operators.bash import BashOperator

# Absolute path to dbt installed in the Dockerfile venv
DBT_BIN = "/usr/local/airflow/dbt_venv/bin/dbt"

# Where your dbt project lives inside the Astro container.
# In your repo, dbt project is: include/youtube_capstone/transform/youtube_analytics
DBT_PROJECT_DIR = "/usr/local/airflow/include/youtube_capstone/transform/youtube_analytics"

# Use the profiles.yml that lives inside the dbt project folder
DBT_PROFILES_DIR = DBT_PROJECT_DIR

# Optional: explicitly set profile/target if you want (safe to omit if profiles.yml defines defaults)
DBT_PROFILE_NAME = os.getenv("DBT_PROFILE_NAME", "youtube_analytics_capstone")
DBT_TARGET = os.getenv("DBT_TARGET", "dev")

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

@dag(
    dag_id="youtube_capstone_dbt",
    description="Runs dbt deps/seed/run/test for YouTube capstone",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule=None,   # manual runs only
    catchup=False,
    tags=["capstone", "dbt", "youtube"],
)
def youtube_capstone_dbt():
    # Helpful debug task so we can SEE what's available inside the container
    dbt_debug_env = BashOperator(
        task_id="dbt_debug_env",
        bash_command=f"""
        set -e
        echo "AIRFLOW_HOME=$AIRFLOW_HOME"
        echo "DBT_PROJECT_DIR={DBT_PROJECT_DIR}"
        echo "DBT_PROFILES_DIR={DBT_PROFILES_DIR}"
        ls -la {DBT_PROJECT_DIR} || true
        echo "dbt binary:" && ls -la {DBT_BIN} || true
        {DBT_BIN} --version
        """,
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"{DBT_BIN} deps --profiles-dir {DBT_PROFILES_DIR} "
            f"--profile {DBT_PROFILE_NAME} --target {DBT_TARGET}"
        ),
    )

    dbt_seed = BashOperator(
    task_id="dbt_seed",
    bash_command=(
        f"cd {DBT_PROJECT_DIR} && "
        f"{DBT_BIN} seed --profiles-dir {DBT_PROFILES_DIR} "
        f"--profile {DBT_PROFILE_NAME} --target {DBT_TARGET} --full-refresh"
    ),
    env={
    "SNOWFLAKE_ACCOUNT": "LYWBBPJ-ODB66944",
    "SNOWFLAKE_HOST": "LYWBBPJ-ODB66944.snowflakecomputing.com",
    "SNOWFLAKE_ROLE": "ALL_USERS_ROLE",
    "SNOWFLAKE_USER": os.environ.get("SNOWFLAKE_USER", ""),
    "SNOWFLAKE_PASSWORD": os.environ.get("SNOWFLAKE_PASSWORD", ""),
    "SNOWFLAKE_DATABASE": os.environ.get("SNOWFLAKE_DATABASE", ""),
    "SNOWFLAKE_WAREHOUSE": os.environ.get("SNOWFLAKE_WAREHOUSE", ""),
    "SNOWFLAKE_SCHEMA": os.environ.get("SNOWFLAKE_SCHEMA", ""),
    "STUDENT_SCHEMA": os.environ.get("STUDENT_SCHEMA", ""),
    "DBT_PROFILES_DIR": str(DBT_PROFILES_DIR),
    "DBT_PROJECT_DIR": str(DBT_PROJECT_DIR),
}
)

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"{DBT_BIN} run --profiles-dir {DBT_PROFILES_DIR} "
            f"--profile {DBT_PROFILE_NAME} --target {DBT_TARGET}"
        ),

    env={
    "SNOWFLAKE_ACCOUNT": "LYWBBPJ-ODB66944",
    "SNOWFLAKE_HOST": "LYWBBPJ-ODB66944.snowflakecomputing.com",
    "SNOWFLAKE_ROLE": "ALL_USERS_ROLE",
    "SNOWFLAKE_USER": os.environ.get("SNOWFLAKE_USER", ""),
    "SNOWFLAKE_PASSWORD": os.environ.get("SNOWFLAKE_PASSWORD", ""),
    "SNOWFLAKE_DATABASE": os.environ.get("SNOWFLAKE_DATABASE", ""),
    "SNOWFLAKE_WAREHOUSE": os.environ.get("SNOWFLAKE_WAREHOUSE", ""),
    "SNOWFLAKE_SCHEMA": os.environ.get("SNOWFLAKE_SCHEMA", ""),
    "STUDENT_SCHEMA": os.environ.get("STUDENT_SCHEMA", ""),
    "DBT_PROFILES_DIR": str(DBT_PROFILES_DIR),
    "DBT_PROJECT_DIR": str(DBT_PROJECT_DIR),
}
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"{DBT_BIN} test --profiles-dir {DBT_PROFILES_DIR} "
            f"--profile {DBT_PROFILE_NAME} --target {DBT_TARGET}"
        ),
    
    env={
    "SNOWFLAKE_ACCOUNT": "LYWBBPJ-ODB66944",
    "SNOWFLAKE_HOST": "LYWBBPJ-ODB66944.snowflakecomputing.com",
    "SNOWFLAKE_ROLE": "ALL_USERS_ROLE",
    "SNOWFLAKE_USER": os.environ.get("SNOWFLAKE_USER", ""),
    "SNOWFLAKE_PASSWORD": os.environ.get("SNOWFLAKE_PASSWORD", ""),
    "SNOWFLAKE_DATABASE": os.environ.get("SNOWFLAKE_DATABASE", ""),
    "SNOWFLAKE_WAREHOUSE": os.environ.get("SNOWFLAKE_WAREHOUSE", ""),
    "SNOWFLAKE_SCHEMA": os.environ.get("SNOWFLAKE_SCHEMA", ""),
    "STUDENT_SCHEMA": os.environ.get("STUDENT_SCHEMA", ""),
    "DBT_PROFILES_DIR": str(DBT_PROFILES_DIR),
    "DBT_PROJECT_DIR": str(DBT_PROJECT_DIR),
}
    )

    dbt_debug_env >> dbt_deps >> dbt_seed >> dbt_run >> dbt_test


youtube_capstone_dbt()