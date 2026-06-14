# Azure Deployment

## Production Slice

The first live-data slice ingests the Bank of Canada Valet mortgage-rate group
once per day. Each run:

1. Downloads the latest official JSON response.
2. Archives the unchanged response in the Blob Storage `bronze` container.
3. Normalizes and upserts rate observations into Azure Database for PostgreSQL.
4. Records run status, row counts, source watermark, code version, and errors.
5. Exposes `/api/health` for uptime and freshness monitoring.

The deployment uses an Azure Functions Consumption plan, Standard LRS Blob
Storage, Application Insights, Log Analytics, and a burstable PostgreSQL B1ms
server with 32 GB of storage.

## Prerequisites

- Azure CLI with Bicep support
- Azure Functions Core Tools 4
- Python 3.11
- An Azure resource group in Canada Central
- A PostgreSQL administrator password stored in Azure Key Vault

Keep secrets out of Git. `local.settings.json` and non-example parameter files
are ignored.

## Provision Resources

```powershell
az login
az account set --subscription "<subscription-id-or-name>"
az group create --name rg-ontario-housing-dev --location canadacentral
az deployment group create `
  --resource-group rg-ontario-housing-dev `
  --template-file infra/main.bicep `
  --parameters infra/main.parameters.json
```

Copy `infra/main.parameters.example.json` to `infra/main.parameters.json` and
replace its placeholders. `baseName` must be globally unique and contain only
lowercase letters and numbers.

## Deploy Function Code

```powershell
Set-Location azure_functions
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
func azure functionapp publish <function-app-name> --python
```

The timer runs daily at 08:15 UTC. To test immediately, enable
`run_on_startup=True` temporarily or invoke the function from the Azure portal.

## Verify

```powershell
Invoke-RestMethod https://<function-app-name>.azurewebsites.net/api/health
```

Confirm that:

- the `bronze` container has a date-partitioned Bank of Canada JSON object;
- `mortgage_rates` contains normalized observations;
- `pipeline_runs` has a successful row with a source watermark;
- Application Insights contains the function invocation and no exceptions.

## Cost Controls

Create a small monthly budget and alerts at 50, 80, and 100 percent. The B1ms
PostgreSQL server is the main continuous cost risk once free credits or monthly
allowances expire. Stop or remove unused development resources, keep Blob
Storage lifecycle rules conservative, and retain only the logs needed for the
portfolio demonstration.

## Security Follow-up

The initial template passes the database password into Function App settings as
a secure deployment parameter. The next hardening step is a managed identity
plus Key Vault references, followed by a restricted PostgreSQL firewall or
private networking when the project moves beyond portfolio-scale usage.
