FROM apache/airflow:3.3.0 AS runtime

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    -r /tmp/requirements.txt

COPY --chown=airflow:root src /opt/airflow/src

ENV PYTHONPATH=/opt/airflow


FROM runtime AS test

COPY requirements-test.txt /tmp/requirements-test.txt

RUN pip install --no-cache-dir -r /tmp/requirements-test.txt

COPY --chown=airflow:root tests /opt/airflow/tests
COPY --chown=airflow:root airflow/dags /opt/airflow/dags