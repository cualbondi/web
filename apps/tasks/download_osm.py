from urllib import request
import os
import sys
from datetime import timedelta, datetime

from airflow import DAG
from airflow.operators.python_operator import PythonOperator


def download_osm(king):
    filename = f'/tmp/osm-{king["name"]}.pbf'
    url = king['url']
    request.urlretrieve(url, filename, lambda nb, bs, fs: progress(nb, bs, fs, url))


def progress(numblocks, blocksize, filesize, url):
    base = os.path.basename(url)
    try:
        percent = min((numblocks * blocksize * 100) / filesize, 100)
    except ZeroDivisionError:
        percent = 100
    if numblocks != 0:
        sys.stdout.write('\b' * 70)
    sys.stdout.write('%-66s%3d%%' % (base, percent))


king = {
    'name': 'argentina',
    'url': 'http://download.geofabrik.de/south-america/argentina-latest.osm.pbf',
    'id': 286393,
    'paradas_completas': False,
}


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime.today(),
    'schedule_interval': '@once'
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
}

dag = DAG(
    'importer', default_args=default_args)


t1 = PythonOperator(
    task_id='download_osm',
    python_callable=download_osm,
    op_kwargs={'king': king},
    dag=dag)
