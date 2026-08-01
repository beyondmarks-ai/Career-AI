[CmdletBinding()]
param(
    [string]$OpenAIResource = 'Rakesh',
    [string]$OpenAIResourceGroup = 'Beyond_Marks',
    [string]$DocumentResource = 'beyondmarks-resource',
    [string]$DocumentResourceGroup = 'rg-beyondmarks',
    [string]$SearchService = 'gdelt-news-search',
    [string]$SearchResourceGroup = 'firecrawl',
    [string]$EnvFile = (Join-Path $PSScriptRoot '.env')
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Environment file not found: $EnvFile"
}

az account show --only-show-errors | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'Azure CLI is not authenticated. Run az login once to retrieve the keys.'
}

$openAIKey = az cognitiveservices account keys list `
    --name $OpenAIResource `
    --resource-group $OpenAIResourceGroup `
    --query key1 `
    --output tsv `
    --only-show-errors
if ($LASTEXITCODE -ne 0 -or -not $openAIKey) {
    throw 'Could not retrieve the Azure OpenAI API key.'
}

$documentKey = az cognitiveservices account keys list `
    --name $DocumentResource `
    --resource-group $DocumentResourceGroup `
    --query key1 `
    --output tsv `
    --only-show-errors
if ($LASTEXITCODE -ne 0 -or -not $documentKey) {
    throw 'Could not retrieve the Document Intelligence API key.'
}

$searchKey = az search admin-key show `
    --service-name $SearchService `
    --resource-group $SearchResourceGroup `
    --query primaryKey `
    --output tsv `
    --only-show-errors
if ($LASTEXITCODE -ne 0 -or -not $searchKey) {
    throw 'Could not retrieve the Azure AI Search admin key.'
}

$values = [ordered]@{
    AZURE_OPENAI_API_KEY = $openAIKey.Trim()
    AZURE_DOCUMENT_INTELLIGENCE_API_KEY = $documentKey.Trim()
    AZURE_SEARCH_API_KEY = $searchKey.Trim()
}

$content = [IO.File]::ReadAllText($EnvFile)
foreach ($entry in $values.GetEnumerator()) {
    $pattern = "(?m)^$([regex]::Escape($entry.Key))=.*$"
    $replacement = "$($entry.Key)=$($entry.Value)"
    if ([regex]::IsMatch($content, $pattern)) {
        $content = [regex]::Replace($content, $pattern, $replacement)
    }
    else {
        $content = "$content`r`n$replacement"
    }
}

$utf8WithoutBom = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText($EnvFile, $content, $utf8WithoutBom)

Write-Host 'Azure API keys were written to the ignored .env file.'
