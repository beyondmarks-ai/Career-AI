[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9-]{2,60}$')]
    [string]$AppName,

    [Parameter(Mandatory = $true)]
    [string]$AzureOpenAIEndpoint,

    [Parameter(Mandatory = $true)]
    [string]$AzureOpenAIDeployment,

    [string]$ResourceGroup = 'careerlens-rg',
    [string]$Location = 'centralindia',
    [string]$AzureOpenAIResourceId = ''
)

$ErrorActionPreference = 'Stop'

az account show --only-show-errors | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'Azure CLI is not authenticated. Run az login and try again.'
}

Write-Host 'Deploying Career AI to Azure App Service...'
az webapp up `
    --name $AppName `
    --resource-group $ResourceGroup `
    --location $Location `
    --runtime 'PYTHON:3.12' `
    --sku B1 `
    --os-type linux `
    --track-status false `
    --only-show-errors
if ($LASTEXITCODE -ne 0) { throw 'Azure App Service deployment failed.' }

az webapp config set `
    --name $AppName `
    --resource-group $ResourceGroup `
    --startup-file 'bash startup.sh' `
    --only-show-errors | Out-Null

az webapp config appsettings set `
    --name $AppName `
    --resource-group $ResourceGroup `
    --settings `
        AZURE_OPENAI_ENDPOINT=$AzureOpenAIEndpoint `
        AZURE_OPENAI_DEPLOYMENT=$AzureOpenAIDeployment `
        AZURE_OPENAI_API_VERSION=2024-10-21 `
        SCM_DO_BUILD_DURING_DEPLOYMENT=true `
    --only-show-errors | Out-Null

$identity = az webapp identity assign `
    --name $AppName `
    --resource-group $ResourceGroup `
    --output json | ConvertFrom-Json

if ($AzureOpenAIResourceId) {
    az role assignment create `
        --assignee-object-id $identity.principalId `
        --assignee-principal-type ServicePrincipal `
        --role 'Cognitive Services OpenAI User' `
        --scope $AzureOpenAIResourceId `
        --only-show-errors | Out-Null
}
else {
    Write-Warning 'Managed Identity was enabled, but no Azure OpenAI resource ID was supplied.'
    Write-Warning 'Grant the app identity the Cognitive Services OpenAI User role before analysis will work.'
}

$url = az webapp show --name $AppName --resource-group $ResourceGroup --query defaultHostName -o tsv
Write-Host "Deployment complete: https://$url"
