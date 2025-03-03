import os
import datetime
from azure.identity import DefaultAzureCredential
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.storage.blob import BlobServiceClient

# Define Constants
SUBSCRIPTION_ID = "your-subscription-id"
PRIMARY_RESOURCE_GROUP = "rg-1"
SECONDARY_RESOURCE_GROUP = "rg-2"
PRIMARY_WEBAPP = "primary-webapp"
SECONDARY_WEBAPP = "secondary-webapp"
PRIMARY_SQL_SERVER = "primary-sql-server"
SECONDARY_SQL_SERVER = "secondary-sql-server"
FAILOVER_GROUP = "your-failover-group"
STORAGE_ACCOUNT_NAME = "failoverlogs"
CONTAINER_NAME = "failoverlogs"
LOG_FILE = "failover_log.txt"

# Authenticate with Azure
credential = DefaultAzureCredential()
web_client = WebSiteManagementClient(credential, SUBSCRIPTION_ID)
sql_client = SqlManagementClient(credential, SUBSCRIPTION_ID)

# Function to log events
def log_event(message):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp}: {message}"
    print(log_entry)
    
    # Write to log file
    with open(LOG_FILE, "a") as log:
        log.write(log_entry + "\n")

# Function to stop a web app
def stop_web_app(resource_group, webapp_name):
    log_event(f"⏳ Stopping Web App: {webapp_name} in {resource_group}")
    web_client.web_apps.stop(resource_group, webapp_name)

# Function to start a web app
def start_web_app(resource_group, webapp_name):
    log_event(f"🔄 Starting Web App: {webapp_name} in {resource_group}")
    web_client.web_apps.start(resource_group, webapp_name)

# Function to check web app status
def check_web_app_status(resource_group, webapp_name):
    app_status = web_client.web_apps.get(resource_group, webapp_name)
    return app_status.state

# Function to stop SQL Server
def stop_sql_server(resource_group, sql_server):
    log_event(f"⏳ Stopping SQL Server: {sql_server} in {resource_group}")
    sql_client.servers.begin_update(resource_group, sql_server, {"state": "Disabled"}).result()

# Function to start SQL Server
def start_sql_server(resource_group, sql_server):
    log_event(f"🔄 Starting SQL Server: {sql_server} in {resource_group}")
    sql_client.servers.begin_update(resource_group, sql_server, {"state": "Enabled"}).result()

# Function to check SQL failover status
def check_failover_status():
    failover_status = sql_client.failover_groups.get(
        PRIMARY_RESOURCE_GROUP, PRIMARY_SQL_SERVER, FAILOVER_GROUP
    )
    return failover_status.replication_role

# Function to upload logs to Azure Storage
def upload_logs():
    try:
        connection_string = f"DefaultEndpointsProtocol=https;AccountName={STORAGE_ACCOUNT_NAME};AccountKey=your-storage-key;EndpointSuffix=core.windows.net"
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=f"failover_log_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}.txt")

        with open(LOG_FILE, "rb") as log_file:
            blob_client.upload_blob(log_file)

        log_event("✅ Log file uploaded to Azure Storage")
    except Exception as e:
        log_event(f"❌ Error uploading log file: {e}")

# --- START FAILOVER TEST ---
log_event("⚡ Failover Test Started ⚡")

# Step 1: Stop Primary Web App & Check Secondary Web App
stop_web_app(PRIMARY_RESOURCE_GROUP, PRIMARY_WEBAPP)
secondary_status = check_web_app_status(SECONDARY_RESOURCE_GROUP, SECONDARY_WEBAPP)
if secondary_status == "Running":
    log_event("✅ Secondary Web App is Active!")
else:
    log_event("❌ Secondary Web App is NOT Running!")

# Restart Primary Web App
start_web_app(PRIMARY_RESOURCE_GROUP, PRIMARY_WEBAPP)

# Step 2: Stop Secondary Web App & Check Primary Web App
stop_web_app(SECONDARY_RESOURCE_GROUP, SECONDARY_WEBAPP)
primary_status = check_web_app_status(PRIMARY_RESOURCE_GROUP, PRIMARY_WEBAPP)
if primary_status == "Running":
    log_event("✅ Primary Web App is Active!")
else:
    log_event("❌ Primary Web App is NOT Running!")

# Restart Secondary Web App
start_web_app(SECONDARY_RESOURCE_GROUP, SECONDARY_WEBAPP)

# Step 3: Stop Primary SQL DB & Check Failover
stop_sql_server(PRIMARY_RESOURCE_GROUP, PRIMARY_SQL_SERVER)
failover_status = check_failover_status()
if failover_status == "Secondary":
    log_event("✅ SQL Failover to Secondary Completed!")
else:
    log_event("❌ SQL Failover NOT Successful!")

# Restart Primary SQL DB
start_sql_server(PRIMARY_RESOURCE_GROUP, PRIMARY_SQL_SERVER)

# Step 4: Stop Secondary SQL DB & Check if Primary Takes Over
stop_sql_server(SECONDARY_RESOURCE_GROUP, SECONDARY_SQL_SERVER)
failover_status = check_failover_status()
if failover_status == "Primary":
    log_event("✅ Primary SQL DB is Handling Queries Again!")
else:
    log_event("❌ Primary SQL DB is NOT Handling Queries!")

# Restart Secondary SQL DB
start_sql_server(SECONDARY_RESOURCE_GROUP, SECONDARY_SQL_SERVER)

log_event("✅ Failover Test Completed")

# Upload logs to Azure Storage
upload_logs()
