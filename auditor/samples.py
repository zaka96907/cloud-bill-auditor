"""Generate realistic demo bills (AWS CUR, GCP billing export, Azure cost details).

Each sample contains 30 days of usage with deliberately planted waste —
idle resources, old instance types, dev boxes running 24/7, a log flood
spike, NAT traffic, snapshots — so every part of the app has something to show.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# (service, resource, usage/sku, region, daily_cost, tags, extra)
_AWS = [
    ("Amazon Elastic Compute Cloud", "i-0a1b2c3d4e5f prod-api-1", "BoxUsage:m5.2xlarge", "us-east-1", 9.2, "env=prod;owner=api", ""),
    ("Amazon Elastic Compute Cloud", "i-0a1b2c3d4e60 prod-api-2", "BoxUsage:m5.2xlarge", "us-east-1", 9.2, "env=prod;owner=api", ""),
    ("Amazon Elastic Compute Cloud", "i-0bb11 legacy-reporting", "BoxUsage:m4.4xlarge", "us-east-1", 19.2, "", ""),
    ("Amazon Elastic Compute Cloud", "i-0cc22 dev-jenkins-build", "BoxUsage:c5.4xlarge", "us-east-1", 16.3, "env=dev", ""),
    ("Amazon Elastic Compute Cloud", "i-0dd33 staging-web", "BoxUsage:t2.xlarge", "eu-west-1", 4.5, "env=staging", ""),
    ("Amazon Elastic Compute Cloud", "i-0ee44 analytics-worker", "BoxUsage:r5.4xlarge (CPU utilization 12%)", "us-east-1", 24.2, "env=prod", ""),
    ("Amazon Elastic Compute Cloud", "vol-0ff55 unattached-volume", "EBS:VolumeUsage.gp2 (unattached)", "us-east-1", 3.3, "", ""),
    ("Amazon Elastic Compute Cloud", "snap-0aa66 old-snapshots", "EBS:SnapshotUsage", "us-east-1", 5.1, "", ""),
    ("Amazon Elastic Compute Cloud", "eipalloc-0ab idle-eip", "ElasticIP:IdleAddress", "us-east-1", 0.12, "", ""),
    ("Amazon Elastic Compute Cloud", "nat-0123 prod-nat", "NatGateway-Bytes", "us-east-1", 7.8, "env=prod", ""),
    ("Amazon Relational Database Service", "db-prod-postgres", "InstanceUsage:db.r5.2xlarge", "us-east-1", 23.0, "env=prod;owner=data", ""),
    ("Amazon Relational Database Service", "db-test-mysql", "InstanceUsage:db.m5.xlarge", "us-east-1", 8.2, "env=test", ""),
    ("Amazon Simple Storage Service", "prod-assets-bucket", "TimedStorage-ByteHrs (S3 Standard)", "us-east-1", 6.4, "env=prod", ""),
    ("Amazon Simple Storage Service", "prod-assets-bucket", "DataTransfer-Out-Bytes", "us-east-1", 4.1, "env=prod", ""),
    ("AmazonCloudWatch", "/aws/lambda/order-processor", "PutLogEvents / DataProcessing-Bytes", "us-east-1", 3.0, "env=prod", "flood"),
    ("AWS Lambda", "order-processor", "Lambda-GB-Second", "us-east-1", 2.2, "env=prod", ""),
    ("Elastic Load Balancing", "app/old-lb (idle)", "LoadBalancerUsage", "us-east-1", 0.6, "", ""),
    ("Amazon EMR", "j-emr-nightly-etl", "BoxUsage:m5.xlarge", "us-east-1", 6.0, "env=prod", ""),
    ("Amazon SageMaker", "notebook-gpu-ml", "ml.p3.2xlarge", "us-east-1", 22.0, "", ""),
]

_GCP = [
    ("Compute Engine", "prod-web-1", "N2 Instance Core running in Americas", "us-central1", 7.5, "env:prod", ""),
    ("Compute Engine", "prod-web-2", "N2 Instance Core running in Americas", "us-central1", 7.5, "env:prod", ""),
    ("Compute Engine", "legacy-batch", "n1-standard-16 Instance (CPU utilization 9%)", "us-central1", 18.0, "", ""),
    ("Compute Engine", "dev-sandbox-vm", "e2-standard-8 Instance", "us-east1", 6.4, "env:dev", ""),
    ("Compute Engine", "orphan-disk-01", "Storage PD Capacity (unattached)", "us-central1", 1.8, "", ""),
    ("Compute Engine", "static-ip-unused", "Static Ip Charge (idle)", "us-central1", 0.24, "", ""),
    ("Compute Engine", "pd-snapshots", "Storage PD Snapshot", "us-central1", 3.2, "", ""),
    ("Compute Engine", "network", "Network Internet Egress from Americas", "us-central1", 5.4, "env:prod", ""),
    ("Cloud SQL", "prod-postgres", "Cloud SQL for PostgreSQL: Zonal - 8 vCPU", "us-central1", 14.0, "env:prod", ""),
    ("Cloud Storage", "media-bucket", "Standard Storage US Multi-region", "us", 5.2, "env:prod", ""),
    ("BigQuery", "analytics", "Analysis (on-demand)", "us", 12.0, "team:data", ""),
    ("Cloud Logging", "k8s-cluster", "Log Volume (ingestion)", "global", 2.6, "", "flood"),
    ("Kubernetes Engine", "gke-prod", "Autopilot Pod vCPU", "us-central1", 11.0, "env:prod", ""),
    ("Dataproc", "nightly-spark-etl", "Dataproc vCPU", "us-central1", 4.0, "team:data", ""),
    ("Vertex AI", "training-gpu", "NVIDIA Tesla T4 GPU", "us-central1", 9.0, "", ""),
]

_AZURE = [
    ("Virtual Machines", "/subscriptions/x/resourceGroups/prod/vm-api-01", "D4s v5", "eastus", 6.9, "env:prod", ""),
    ("Virtual Machines", "/subscriptions/x/resourceGroups/prod/vm-api-02", "D4s v5", "eastus", 6.9, "env:prod", ""),
    ("Virtual Machines", "/subscriptions/x/resourceGroups/legacy/vm-legacy", "Standard_D14_v2", "eastus", 22.0, "", ""),
    ("Virtual Machines", "/subscriptions/x/resourceGroups/dev/vm-dev-test", "Standard_D8s_v3", "westeurope", 9.2, "env:dev", ""),
    ("Storage", "/subscriptions/x/resourceGroups/prod/disk-orphan", "Premium SSD Managed Disks (unattached)", "eastus", 4.4, "", ""),
    ("Storage", "/subscriptions/x/resourceGroups/prod/snapshots", "Snapshots LRS", "eastus", 2.7, "", ""),
    ("Storage", "/subscriptions/x/resourceGroups/prod/blobs", "Hot LRS Blob Storage", "eastus", 4.9, "env:prod", ""),
    ("SQL Database", "/subscriptions/x/resourceGroups/prod/sql-prod", "vCore General Purpose", "eastus", 16.0, "env:prod", ""),
    ("Log Analytics", "/subscriptions/x/resourceGroups/prod/law-prod", "Log Analytics data ingestion", "eastus", 3.5, "", "flood"),
    ("Bandwidth", "/subscriptions/x/resourceGroups/prod/egress", "Data Transfer Out", "eastus", 3.9, "env:prod", ""),
    ("Virtual Network", "/subscriptions/x/resourceGroups/prod/pip-unused", "Standard IPv4 Static Public IP (idle)", "eastus", 0.12, "", ""),
    ("Azure Kubernetes Service", "/subscriptions/x/resourceGroups/prod/aks", "Standard_D8s_v5 nodes (CPU utilization 18%)", "eastus", 18.5, "env:prod", ""),
    ("Azure Batch", "/subscriptions/x/resourceGroups/data/batch-render", "Batch render worker D16", "eastus", 7.0, "team:data", ""),
]


def _series(base: float, days: int, rng: np.random.Generator, flood: bool) -> np.ndarray:
    weekly = 1 + 0.06 * np.sin(np.arange(days) / 7 * 2 * np.pi)
    noise = rng.normal(1.0, 0.04, days)
    vals = base * weekly * noise
    if flood:
        vals[days - 9: days - 6] *= 9.0   # a 3-day error-loop log flood
    return np.clip(vals, 0, None).round(4)


def generate(provider: str = "AWS", days: int = 30, seed: int = 7,
             end: str | pd.Timestamp | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end_ts = pd.Timestamp(end) if end is not None else pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
    dates = pd.date_range(end=end_ts, periods=days, freq="D")
    spec = {"AWS": _AWS, "GCP": _GCP, "Azure": _AZURE}[provider]

    rows = []
    for service, resource, usage, region, base, tags, extra in spec:
        for d, cost in zip(dates, _series(base, days, rng, extra == "flood")):
            rows.append((service, resource, usage, region, d, float(cost), tags))

    df = pd.DataFrame(rows, columns=["service", "resource", "usage", "region", "date", "cost", "tags"])

    if provider == "AWS":
        return pd.DataFrame({
            "bill/PayerAccountId": "111122223333",
            "lineItem/UsageAccountId": np.where(df["tags"].str.contains("dev|test|staging"), "444455556666", "111122223333"),
            "lineItem/UsageStartDate": df["date"].dt.strftime("%Y-%m-%dT00:00:00Z"),
            "lineItem/ProductCode": df["service"],
            "lineItem/ResourceId": df["resource"],
            "lineItem/UsageType": df["usage"],
            "product/region": df["region"],
            "lineItem/UnblendedCost": df["cost"],
            "resourceTags/user:env": df["tags"].str.extract(r"env=(\w+)")[0].fillna(""),
            "resourceTags/user:owner": df["tags"].str.extract(r"owner=(\w+)")[0].fillna(""),
        })
    if provider == "GCP":
        return pd.DataFrame({
            "Billing account ID": "01ABCD-234567-89EFGH",
            "Project ID": np.where(df["tags"].str.contains("dev"), "acme-dev", "acme-prod"),
            "Service description": df["service"],
            "SKU description": df["usage"],
            "Resource name": df["resource"],
            "Usage start date": df["date"].dt.strftime("%Y-%m-%d"),
            "Region/Zone": df["region"],
            "Cost ($)": df["cost"],
            "Labels": df["tags"],
        })
    return pd.DataFrame({
        "SubscriptionName": np.where(df["tags"].str.contains("dev"), "Dev-Test", "Production"),
        "ResourceGroup": df["resource"].str.extract(r"resourceGroups/(\w+)")[0],
        "Date": df["date"].dt.strftime("%m/%d/%Y"),
        "MeterCategory": df["service"],
        "MeterName": df["usage"],
        "ResourceId": df["resource"],
        "ResourceLocation": df["region"],
        "CostInBillingCurrency": df["cost"],
        "Tags": df["tags"].map(lambda t: "{" + t.replace(":", '": "').join(['"', '"']) + "}" if t else ""),
    })
