import argparse

import docker
import uvicorn

from fastapi import FastAPI
from prometheus_client import make_asgi_app
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from prometheus_client.registry import Collector


# Create app
app = FastAPI(debug=False)

# Add prometheus asgi middleware to route /metrics requests
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


class ContainerCollector(Collector):
    def collect(self):
        client = docker.from_env()
        containers = client.containers.list(all=True)

        container_running_status = GaugeMetricFamily(
            "container_running_status",
            "容器运行状态",
            labels=["name", "status"],
        )
        container_pid = GaugeMetricFamily(
            "container_pid",
            "容器PID",
            labels=["name", "status"],
        )

        for container in containers:
            name = container.name
            status = container.status
            pid = container.attrs["State"]["Pid"]

            if status != "running":
                container_running_status.add_metric([name, status], 0)
            else:
                container_running_status.add_metric([name, status], 1)
                container_pid.add_metric([name, status], pid)
        yield container_running_status
        yield container_pid

REGISTRY.register(ContainerCollector())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=9324, help="Bind socket to this port.")
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=int(args.port), reload=False)
