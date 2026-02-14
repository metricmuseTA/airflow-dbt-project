FROM quay.io/astronomer/astro-runtime:11.3.0

# Create a separate venv for dbt so it doesn't fight Airflow's pinned constraints
RUN python -m venv /usr/local/airflow/dbt_venv \
 && /usr/local/airflow/dbt_venv/bin/pip install --no-cache-dir --upgrade pip \
 && /usr/local/airflow/dbt_venv/bin/pip install --no-cache-dir dbt-core==1.9.4 dbt-snowflake==1.9.1

# (optional) make dbt visible on PATH
ENV PATH="/usr/local/airflow/dbt_venv/bin:${PATH}"