#!/bin/bash

# Define Variables
PRIMARY_RESOURCE_GROUP="rg-1"
SECONDARY_RESOURCE_GROUP="rg-2"
PRIMARY_WEBAPP="primary-webapp"
SECONDARY_WEBAPP="secondary-webapp"
PRIMARY_SQL="primary-sql-server"
SECONDARY_SQL="secondary-sql-server"
FAILOVER_GROUP="your-failover-group"
LOG_FILE="failover_log.txt"
STORAGE_ACCOUNT="failoverlogs"
CONTAINER_NAME="failoverlogs"

# Function to Log Events
log_event() {
    echo "$(date): $1" | tee -a $LOG_FILE
}

# Start Logging
log_event "⚡ Failover Test Started ⚡"

### --- Step 1: Stop Primary Web App in Germany West Central ---
log_event "⏳ Stopping Primary Web App: $PRIMARY_WEBAPP in $PRIMARY_RESOURCE_GROUP (Germany West Central)"
az webapp stop --name $PRIMARY_WEBAPP --resource-group $PRIMARY_RESOURCE_GROUP
sleep 30  # Wait for failover

# Check Secondary Web App Status in Germany North
STATUS=$(az webapp show --name $SECONDARY_WEBAPP --resource-group $SECONDARY_RESOURCE_GROUP --query "state" --output tsv)
if [[ "$STATUS" == "Running" ]]; then
    log_event "✅ Secondary Web App ($SECONDARY_WEBAPP in Germany North) is Active!"
else
    log_event "❌ Secondary Web App is NOT Running!"
fi

### --- Step 2: Stop Secondary Web App in Germany North ---
log_event "⏳ Stopping Secondary Web App: $SECONDARY_WEBAPP in $SECONDARY_RESOURCE_GROUP (Germany North)"
az webapp stop --name $SECONDARY_WEBAPP --resource-group $SECONDARY_RESOURCE_GROUP
sleep 30

# Verify both Web Apps are stopped
PRIMARY_STATUS=$(az webapp show --name $PRIMARY_WEBAPP --resource-group $PRIMARY_RESOURCE_GROUP --query "state" --output tsv)
SECONDARY_STATUS=$(az webapp show --name $SECONDARY_WEBAPP --resource-group $SECONDARY_RESOURCE_GROUP --query "state" --output tsv)

if [[ "$PRIMARY_STATUS" == "Stopped" && "$SECONDARY_STATUS" == "Stopped" ]]; then
    log_event "❌ Both Web Apps are Down. No Failover Available!"
else
    log_event "✅ Failover Mechanism Handled Web App Failure!"
fi

### --- Step 3: Stop Primary SQL DB in Germany West Central ---
log_event "⏳ Stopping Primary SQL DB: $PRIMARY_SQL in $PRIMARY_RESOURCE_GROUP"
az sql server stop --name $PRIMARY_SQL --resource-group $PRIMARY_RESOURCE_GROUP
sleep 30

# Check Failover Group Status
FAILOVER_STATUS=$(az sql failover-group show --resource-group $PRIMARY_RESOURCE_GROUP --server $PRIMARY_SQL --name $FAILOVER_GROUP --query "replicationRole" --output tsv)
if [[ "$FAILOVER_STATUS" == "Secondary" ]]; then
    log_event "✅ SQL Failover to Secondary Completed!"
else
    log_event "❌ SQL Failover NOT Successful!"
fi

### --- Step 4: Stop Secondary SQL DB in Germany North ---
log_event "⏳ Stopping Secondary SQL DB: $SECONDARY_SQL in $SECONDARY_RESOURCE_GROUP"
az sql server stop --name $SECONDARY_SQL --resource-group $SECONDARY_RESOURCE_GROUP
sleep 30

# Verify both SQL Databases are stopped
PRIMARY_DB_STATUS=$(az sql server show --name $PRIMARY_SQL --resource-group $PRIMARY_RESOURCE_GROUP --query "state" --output tsv)
SECONDARY_DB_STATUS=$(az sql server show --name $SECONDARY_SQL --resource-group $SECONDARY_RESOURCE_GROUP --query "state" --output tsv)

if [[ "$PRIMARY_DB_STATUS" == "Stopped" && "$SECONDARY_DB_STATUS" == "Stopped" ]]; then
    log_event "❌ Both SQL Databases are Down. No Failover Available!"
else
    log_event "✅ Failover Mechanism Handled SQL Database Failure!"
fi

### --- Step 5: Restart Primary Web App, Secondary Web App, and SQL DB ---
log_event "🔄 Restarting Primary & Secondary Web Apps & SQL DBs"
az webapp start --name $PRIMARY_WEBAPP --resource-group $PRIMARY_RESOURCE_GROUP
az webapp start --name $SECONDARY_WEBAPP --resource-group $SECONDARY_RESOURCE_GROUP
az sql server start --name $PRIMARY_SQL --resource-group $PRIMARY_RESOURCE_GROUP
az sql server start --name $SECONDARY_SQL --resource-group $SECONDARY_RESOURCE_GROUP

log_event "✅ Failover Test Completed"

# Upload Log to Azure Storage
az storage blob upload --account-name $STORAGE_ACCOUNT --container-name $CONTAINER_NAME --name failover_log_$(date +"%Y%m%d%H%M%S").txt --file $LOG_FILE

