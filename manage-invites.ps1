[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('New', 'Revoke', 'List')]
    [string]$Action,
    [string]$InviteCode = '',
    [ValidateRange(1, 1000)]
    [int]$MaxUses = 1,
    [ValidateRange(1, 730)]
    [int]$ExpiresInDays = 30,
    [string]$ResourceGroup = 'career-ai-rg',
    [string]$StorageAccount = 'careerauth617db570',
    [string]$TableName = 'CareerInvites'
)

$ErrorActionPreference = 'Stop'
az account show --only-show-errors | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Run az login before managing invites.' }

$accountKey = az storage account keys list `
    --account-name $StorageAccount `
    --resource-group $ResourceGroup `
    --query '[0].value' `
    --output tsv `
    --only-show-errors
if (-not $accountKey) { throw 'Could not retrieve the invite storage account key.' }
$env:AZURE_STORAGE_ACCOUNT = $StorageAccount
$env:AZURE_STORAGE_KEY = $accountKey

function Get-CodeHash([string]$Code) {
    $normalized = ($Code.Trim().ToUpperInvariant() -replace '\s', '')
    $bytes = [Text.Encoding]::UTF8.GetBytes($normalized)
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try { $digest = $sha256.ComputeHash($bytes) } finally { $sha256.Dispose() }
    return ([BitConverter]::ToString($digest) -replace '-', '').ToLowerInvariant()
}

if ($Action -eq 'New') {
    if (-not $InviteCode) {
        $random = New-Object byte[] 18
        $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $generator.GetBytes($random) } finally { $generator.Dispose() }
        $token = [Convert]::ToBase64String($random).TrimEnd('=').Replace('+', '').Replace('/', '')
        $InviteCode = "CA-$($token.ToUpperInvariant())"
    }
    if (($InviteCode -replace '\s', '').Length -lt 12) {
        throw 'Invite codes must contain at least 12 non-whitespace characters.'
    }
    $rowKey = Get-CodeHash $InviteCode
    $created = [DateTime]::UtcNow.ToString('o')
    $expires = [DateTime]::UtcNow.AddDays($ExpiresInDays).ToString('o')
    $entity = @(
        'PartitionKey=invite', "RowKey=$rowKey", 'Enabled=true',
        'Enabled@odata.type=Edm.Boolean', "MaxUses=$MaxUses",
        'MaxUses@odata.type=Edm.Int32', 'Uses=0', 'Uses@odata.type=Edm.Int32',
        "CreatedAt=$created", "ExpiresAt=$expires"
    )
    az storage entity insert --table-name $TableName --entity $entity `
        --if-exists fail --only-show-errors --output none
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the invite code.' }
    [PSCustomObject]@{ InviteCode = $InviteCode; MaxUses = $MaxUses; ExpiresUtc = $expires }
}
elseif ($Action -eq 'Revoke') {
    if (-not $InviteCode) { throw 'Pass -InviteCode with the code to revoke.' }
    $rowKey = Get-CodeHash $InviteCode
    $entity = @(
        'PartitionKey=invite', "RowKey=$rowKey", 'Enabled=false',
        'Enabled@odata.type=Edm.Boolean', "RevokedAt=$([DateTime]::UtcNow.ToString('o'))"
    )
    az storage entity merge --table-name $TableName --entity $entity `
        --only-show-errors --output none
    if ($LASTEXITCODE -ne 0) { throw 'Could not revoke the invite code.' }
    Write-Host 'Invite revoked. Existing sessions created by this invite are now blocked.'
}
else {
    az storage entity query --table-name $TableName `
        --filter "PartitionKey eq 'invite'" `
        --query "items[].{Hash:RowKey,Enabled:Enabled,Uses:Uses,MaxUses:MaxUses,Created:CreatedAt,Expires:ExpiresAt,LastUsed:LastUsedAt}" `
        --only-show-errors --output table
}
