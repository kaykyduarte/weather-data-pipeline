FROM apache/airflow:3.3.0

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    -r /tmp/requirements.txt

COPY --chown=airflow:root src /opt/airflow/src

ENV PYTHONPATH=/opt/airflow