# Step 8: Optional - run your repair analyzer from the CLI

You improved the repair extractor in Step 6. Now call that same analyzer from PowerShell instead of CU Studio, and inspect its saved JSON.

**Time:** about 5-10 minutes once the CLI is installed and sign-in is complete.

**You need:** the updated repair analyzer from Step 6, built and **Ready**, and the endpoint of the Azure Content Understanding resource containing it. Use the single-document repair analyzer, not the classifier/router.

This exercise analyzes only packet 8's repair estimate. **Azure charges apply.** It does not update the Workbench, its saved results, or its business-rule checks. No Copilot or extra lab helper is required.

## 1. Sign in

Keep the Workbench running. Open a separate **Windows PowerShell** window:

```PowerShell
Set-Location "C:\Users\LabUser\Desktop\ignite26-LAB664"
azd auth login
```

Use the Azure lab account from the **Resources** tab. Earlier Studio or `az login` sign-in does not replace this sign-in. Do not put credentials in the commands.

Run the following command blocks in order. **If a command reports an error, stop and ask the proctor before continuing or retrying.**

## 2. Choose your resource and updated analyzer

Replace the two placeholders below. Copy the exact **updated repair analyzer ID from Step 6**. Get the resource endpoint from its **Keys and Endpoint** page in the Azure portal; it must be a resource-root URL, not a Studio or Foundry project URL.

```PowerShell
$env:CU_ENDPOINT = "https://YOUR-LAB-RESOURCE.services.ai.azure.com"
$env:CU_API_VERSION = "2026-06-01-preview"
$AnalyzerId = "YOUR-UPDATED-REPAIR-ANALYZER-ID"
```

These settings apply only to this PowerShell session. Selecting the Preview API here avoids repeating it in the analysis command.

## 3. Analyze the repair estimate

This is the **one billable analysis** in this exercise. The timestamp gives the output a new filename in the VM's existing temporary folder; there is no folder setup or cache management.

```PowerShell
$ResultFile = "$env:TEMP\lab664-repair-$(Get-Date -Format yyyyMMdd-HHmmss).json"

azd ai cu analyze ".\data\documents\packet-08\05-estimate.pdf" `
  --analyzer $AnalyzerId --output json --output-file $ResultFile --on-existing error
```

Wait for successful completion before moving on. `--output json` saves the complete service response.

## 4. Open the saved result

Open the saved JSON in Notepad. This does not call Azure again:

```PowerShell
notepad.exe $ResultFile
```

Confirm `status` is `Succeeded`, `analyzerId` is yours, and `apiVersion` is `2026-06-01-preview`.

In Notepad, use **Ctrl+F** to find `LineItems`, `PartsAmount`, `LaborAmount`, and `SubtotalAmount`. Inside each line item's `valueObject`, inspect the amounts. Number fields use `valueNumber`; the invoice `TotalAmount` uses a nested currency object's `Amount`.

Compare the values with `C:\Users\LabUser\Desktop\ignite26-LAB664\data\documents\packet-08\05-estimate.pdf` and your Step 6 Studio result. The Step 6 reference is:

| Line item | PartsAmount | LaborAmount | TotalAmount.Amount |
|---|---:|---:|---:|
| 0 | 980.00 | 223.20 | 1203.20 |
| 1 | 124.00 | 62.00 | 186.00 |
| 2 | 0.00 | 210.80 | 210.80 |

The line totals sum to the explicit subtotal of **1600.00**. A fresh model run can differ; check the actual PDF and returned values rather than assuming these numbers are guaranteed. Missing parts/labor fields may indicate the wrong analyzer version was selected; confirm the fields are inside `LineItems` and the updated analyzer was built successfully.

**Checkpoint:** the analyzer you improved in Studio can also be called from the CLI. You saved and inspected a fresh extraction without changing the app.

## If something goes wrong

| Symptom | What to check |
|---|---|
| `azd` or `azd ai cu` unavailable | Ask the proctor to complete the CLI setup below. |
| Access denied or analyzer not found | Correct lab account, resource endpoint, exact updated analyzer ID, and **Ready** status. Ask the lab owner about data-plane permissions. |
| Input file not found | Confirm PowerShell is in the repository root and `data\documents\packet-08\05-estimate.pdf` exists. |
| Model readiness warning | Ask the lab owner; do not deploy models or change shared mappings. |
| Failed or slow analysis | Keep the exact error. Do not repeatedly submit paid requests to diagnose it. |

To inspect the JSON again, repeat step 4; do not rerun analysis. For an intentional fresh test, repeat step 3 to generate a new filename. Original files are retained until the VM's temporary files are cleaned up.

## Proctor preparation only

Preinstall Azure Developer CLI (`azd`) **1.37.0 or later** and the Content Understanding extension. `azd` is different from Azure CLI (`az`).

- Check with `azd version` and `azd ai cu version`.
- If `azd` is missing, run `winget install microsoft.azd`, then reopen PowerShell. If installation is blocked, use the lab owner's approved installation process.
- If only the extension is missing, run `azd ext install azure.ai.content-understanding`.
- After setting the resource and API version in step 2, use `azd ai cu doctor` if connection troubleshooting is needed. Inspect model readiness as well as errors. Do not change shared defaults or run `doctor --fix-defaults`.

References: [CLI quickstart](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/quickstart/use-content-understanding-cli?tabs=powershell) and [Azure Developer CLI installation](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd).
