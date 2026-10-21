"""Publish the public website now (the daily DAG run does the same at its end).

PowerShell, from the project folder:
  Get-Content scripts\\publish_site.py -Raw | docker compose exec -T airflow-scheduler python -
"""
import os
import sys

sys.path.insert(0, "/opt/airflow/dags")

from airflow.providers.postgres.hooks.postgres import PostgresHook  # noqa: E402

from jobradar import site_export  # noqa: E402

conn = PostgresHook(postgres_conn_id="jobradar_wh").get_conn()
try:
    sha = site_export.publish_from_env(conn)
finally:
    conn.close()
if sha:
    owner, _, repo = os.environ.get("SITE_REPO", "").partition("/")
    domain = site_export.clean_domain(os.environ.get("SITE_DOMAIN", ""))
    site = f"https://{domain}/" if domain else f"https://{owner.lower()}.github.io/{repo}/"
    print(f"Published (commit {sha[:7]}). Site: {site}")
    print(f"Custom domain: {domain} (CNAME file included)" if domain else "Custom domain: none (SITE_DOMAIN is empty)")
    print("First time only: GitHub repo Settings -> Pages -> Deploy from branch 'gh-pages', folder '/ (root)'.")
else:
    print("Not published: set SITE_GITHUB_TOKEN and SITE_REPO in .env, then run `docker compose up -d`.")
    sys.exit(1)
