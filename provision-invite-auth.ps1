[CmdletBinding()]
param(
    [string]$ResourceGroup = 'career-ai-rg',
    [string]$Location = 'centralindia',
    [string]$StorageAccount = 'careerauth617db570',
    [string]$TableName = 'CareerInvites',
    [string]$PolicyName = 'career-ai-vercel'
)

$ErrorActionPreference = 'Stop'
az account show --only-show-errors | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Run az login before provisioning invite access.' }

az group create --name $ResourceGroup --location $Location --only-show-errors --output none
if ($LASTEXITCODE -ne 0) { throw 'Could not create the invite resource group.' }

$exists = az storage account check-name --name $StorageAccount --query nameAvailable -o tsv
if ($exists -eq 'true') {
    az storage account create `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku Standard_LRS `
        --kind StorageV2 `
        --https-only true `
        --min-tls-version TLS1_2 `
        --allow-blob-public-access false `
        --public-network-access Enabled `
        --only-show-errors `
        --output none
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the invite storage account.' }
}

$accountKey = az storage account keys list `
    --account-name $StorageAccount `
    --resource-group $ResourceGroup `
    --query '[0].value' `
    --output tsv `
    --only-show-errors
if (-not $accountKey) { throw 'Could not retrieve the invite storage account key.' }

$env:AZURE_STORAGE_ACCOUNT = $StorageAccount
$env:AZURE_STORAGE_KEY = $accountKey
az storage table create --name $TableName --only-show-errors --output none
if ($LASTEXITCODE -ne 0) { throw 'Could not create the invite table.' }

$expiry = [DateTime]::UtcNow.AddYears(2).ToString('yyyy-MM-ddTHH:mm:ssZ')
az storage table policy create `
    --name $PolicyName `
    --table-name $TableName `
    --permissions raud `
    --expiry $expiry `
    --only-show-errors `
    --output none
if ($LASTEXITCODE -ne 0) {
    az storage table policy update `
        --name $PolicyName `
        --table-name $TableName `
        --permissions raud `
        --expiry $expiry `
        --only-show-errors `
        --output none
}

[PSCustomObject]@{
    ResourceGroup = $ResourceGroup
    Location = $Location
    StorageAccount = $StorageAccount
    TableName = $TableName
    AccessPolicy = $PolicyName
    PolicyExpiresUtc = $expiry
}
