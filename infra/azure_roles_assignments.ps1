$env:PSExecutionPolicyPreference = 'Bypass'

$ErrorActionPreference = 'Stop'

try {
    function Grant-Role {
        param(
            [string]$PrincipalId,
            [string]$RoleDefinitionId,
            [string]$Scope,
            [string]$Label
        )

        $assignment = Get-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionId $RoleDefinitionId -Scope $Scope -ErrorAction Stop |
            Where-Object { $_.Scope -eq $Scope }

        if (-not $assignment) {
            New-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionId $RoleDefinitionId -Scope $Scope -ErrorAction Stop | Out-Null
        }

        for ($attempt = 1; $attempt -le 10; $attempt++) {
            $assignment = Get-AzRoleAssignment -ObjectId $PrincipalId -RoleDefinitionId $RoleDefinitionId -Scope $Scope -ErrorAction Stop |
                Where-Object { $_.Scope -eq $Scope }
            if ($assignment) {
                Write-Host "Verified $Label for principal '$PrincipalId' at '$Scope'."
                return
            }

            if ($attempt -lt 10) {
                Write-Host "Waiting for $Label assignment to become visible (attempt $attempt of 10)."
                Start-Sleep -Seconds 15
            }
        }

        throw "$Label was not assigned to principal '$PrincipalId' at '$Scope' after 10 verification attempts."
    }

    $appId = '@lab.CloudSubscription.AppId'
    $appSecret = '@lab.CloudSubscription.AppSecret'
    $tenantId = '@lab.CloudSubscription.TenantId'
    $subscriptionId = '@lab.CloudSubscription.Id'
    $resourceGroupName = '@lab.CloudResourceGroup(ResourceGroup1).Name'
    $userUpn = '@lab.CloudPortalCredential(User1).Username'
    $foundryAccountName = 'aifoundry-@lab.LabInstance.Id'
    $searchServiceName = 'search-@lab.LabInstance.Id'

    $securePassword = ConvertTo-SecureString $appSecret -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential ($appId, $securePassword)

    Connect-AzAccount `
        -ServicePrincipal `
        -Tenant $tenantId `
        -Credential $credential `
        -Subscription $subscriptionId `
        -SkipContextPopulation | Out-Null

    $user = Get-AzADUser -UserPrincipalName $userUpn -ErrorAction Stop

    $storageAccount = Get-AzResource `
        -ResourceGroupName $resourceGroupName `
        -ResourceType 'Microsoft.Storage/storageAccounts' `
        -ErrorAction Stop |
        Where-Object { $_.Name -like 'st*' } |
        Select-Object -First 1

    if (-not $storageAccount.ResourceId) {
        throw "No lab storage account was found in resource group '$resourceGroupName'."
    }

    $foundryAccount = Get-AzCognitiveServicesAccount `
        -ResourceGroupName $resourceGroupName `
        -Name $foundryAccountName `
        -ErrorAction Stop

    $foundryPrincipalId = $foundryAccount.Identity.PrincipalId

    if (-not $foundryPrincipalId) {
        throw 'Foundry resource does not have a managed identity PrincipalId.'
    }

    $searchService = Get-AzResource `
        -ResourceGroupName $resourceGroupName `
        -ResourceType 'Microsoft.Search/searchServices' `
        -Name $searchServiceName `
        -ExpandProperties `
        -ErrorAction Stop

    $searchPrincipalId = $searchService.Identity.PrincipalId
    if (-not $searchService.ResourceId -or -not $searchPrincipalId) {
        throw "Search service '$searchServiceName' is missing or does not have a managed identity PrincipalId."
    }

    if (-not $foundryAccount.Endpoint) {
        throw "Foundry resource '$foundryAccountName' did not return an endpoint."
    }

    $cuEndpoint = $foundryAccount.Endpoint.TrimEnd('/')
    $env:CU_ENDPOINT = $cuEndpoint
    [Environment]::SetEnvironmentVariable('CU_ENDPOINT', $cuEndpoint, 'Machine')

    $storageRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    $foundryRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
    $storageReaderRoleId = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    $searchContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
    $searchReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
    $cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'

    Grant-Role -PrincipalId $user.Id -RoleDefinitionId $storageRoleId -Scope $storageAccount.ResourceId -Label 'Storage Blob Data Contributor'
    Grant-Role -PrincipalId $user.Id -RoleDefinitionId $foundryRoleId -Scope $foundryAccount.Id -Label 'Foundry User'
    Grant-Role -PrincipalId $user.Id -RoleDefinitionId $searchContributorRoleId -Scope $searchService.ResourceId -Label 'Search Service Contributor'
    Grant-Role -PrincipalId $user.Id -RoleDefinitionId $searchReaderRoleId -Scope $searchService.ResourceId -Label 'Search Index Data Reader'

    Grant-Role -PrincipalId $foundryPrincipalId -RoleDefinitionId $storageRoleId -Scope $storageAccount.ResourceId -Label 'Storage Blob Data Contributor'
    Grant-Role -PrincipalId $searchPrincipalId -RoleDefinitionId $storageReaderRoleId -Scope $storageAccount.ResourceId -Label 'Storage Blob Data Reader'
    Grant-Role -PrincipalId $searchPrincipalId -RoleDefinitionId $cognitiveServicesUserRoleId -Scope $foundryAccount.Id -Label 'Cognitive Services User'

    Write-Host 'Required resource-scoped role assignments are present. Data-plane propagation and the custom claim analyzer must still pass setup preflight.'
}
catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}