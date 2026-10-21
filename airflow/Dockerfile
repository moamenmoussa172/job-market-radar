ARG AIRFLOW_VERSION=3.3.2
FROM apache/airflow:${AIRFLOW_VERSION}

ARG AIRFLOW_VERSION

# git publishes the website (one "git push" instead of thousands of GitHub API calls)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

# dbt lives in its own virtualenv so its dependencies never clash with Airflow's.
# (The Airflow image sets PIP_USER=true, which breaks pip inside a venv.)
COPY requirements-dbt.txt /requirements-dbt.txt
RUN python -m venv /home/airflow/dbt_venv \
 && PIP_USER=false /home/airflow/dbt_venv/bin/pip install --no-cache-dir -r /requirements-dbt.txt
ENV PATH="${PATH}:/home/airflow/dbt_venv/bin"
