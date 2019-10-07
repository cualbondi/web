from prefect.engine.executors import DaskExecutor
from apps.tasks.tasks.download_osm.download_osm import flow

executor = DaskExecutor(address="tcp://dask-scheduler:8786")
flow.run(executor=executor)
