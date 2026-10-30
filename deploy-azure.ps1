[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9-]{2,60}$')]
    [string]$AppName,

    [Parameter(Mandatory = $true)]
    [string]$AzureOpenAIEndpoint,

    [Parameter(Mandatory = $true)]
    [string]$AzureOpenAIDeployment,

    [string]$AzureOpenAIEmbeddingDeployment = '',
    [string]$DocumentIntelligenceEndpoint = '',
    [string]$DocumentIntelligenceResourceId = '',
    [string]$AzureSearchEndpoint = '',
    [string]$AzureSearchIndex = 'career-ai-resumes',
    [string]$AzureSearchResourceId = '',
    [string]$JoobleApiKey = '',
    [string]$ResourceGroup = 'careerlens-rg',
    [string]$Location = 'centralindia',
    [ValidateSet('F1', 'B1', 'B2', 'B3', 'P1V3', 'P2V3')]
    [string]$Sku = 'F1',
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
    --sku $Sku `
    --os-type linux `
    --track-status false `
    --only-show-errors
if ($LASTEXITCODE -ne 0) { throw 'Azure App Service deployment failed.' }

az webapp config set `
    --name $AppName `
    --resource-group $ResourceGroup `
    --startup-file 'bash startup.sh' `
    --only-show-errors | Out-Null

$appSettings = @(
    "AZURE_OPENAI_ENDPOINT=$AzureOpenAIEndpoint"
    "AZURE_OPENAI_DEPLOYMENT=$AzureOpenAIDeployment"
    'AZURE_OPENAI_API_VERSION=2024-10-21'
    'SCM_DO_BUILD_DURING_DEPLOYMENT=true'
)
if ($AzureOpenAIEmbeddingDeployment) {
    $appSettings += "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$AzureOpenAIEmbeddingDeployment"
}
if ($DocumentIntelligenceEndpoint) {
    $appSettings += "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=$DocumentIntelligenceEndpoint"
}
if ($AzureSearchEndpoint) {
    $appSettings += "AZURE_SEARCH_ENDPOINT=$AzureSearchEndpoint"
    $appSettings += "AZURE_SEARCH_INDEX=$AzureSearchIndex"
}
if ($JoobleApiKey) {
    $appSettings += "JOOBLE_API_KEY=$JoobleApiKey"
}

az webapp config appsettings set `
    --name $AppName `
    --resource-group $ResourceGroup `
    --settings $appSettings `
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

if ($DocumentIntelligenceResourceId) {
    az role assignment create `
        --assignee-object-id $identity.principalId `
        --assignee-principal-type ServicePrincipal `
        --role 'Cognitive Services User' `
        --scope $DocumentIntelligenceResourceId `
        --only-show-errors | Out-Null
}

if ($AzureSearchResourceId) {
    $searchIndexScope = "$AzureSearchResourceId/indexes/$AzureSearchIndex"
    az role assignment create `
        --assignee-object-id $identity.principalId `
        --assignee-principal-type ServicePrincipal `
        --role 'Search Index Data Contributor' `
        --scope $searchIndexScope `
        --only-show-errors | Out-Null
}

$url = az webapp show --name $AppName --resource-group $ResourceGroup --query defaultHostName -o tsv
Write-Host "Deployment complete: https://$url"
