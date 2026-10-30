Content Understanding / hands-on lab

# From documents to an Insurance Workbench

Follow these five steps in order: try prebuilts, customize extraction, classify a packet, add extraction routes, and use a **separate application** to compare policy checks with and without Azure Search retrieval. This guide contains all lab instructions.

Use [CU Studio](https://contentunderstanding.ai.azure.com/) for steps 1-4. Sign in and select your approved Azure resource. You need permission to use Content Understanding, build analyzers, and use the resource's configured models. Studio tests and live app analysis incur Azure charges.

- [1. Prebuilt](#step-1-explore-prebuilt-analyzers)
- [2. Custom](#step-2-build-a-custom-repair-extractor)
- [3. Classifier](#step-3-classify-and-split-a-packet-without-extraction)
- [4. Classifier + routes](#step-4-add-extraction-routes-to-the-classifier)
- [5. Your app](#step-5-connect-to-your-separate-insurance-workbench-app)

===

## Step 1: Explore prebuilt analyzers

> [!Note] **Upload from `data\step1`:** [towing-invoice.pdf](../data/step1/towing-invoice.pdf) (1 page), [demo-id.pdf](../data/step1/demo-id.pdf) (1 page), and [form-1099a.pdf](../data/step1/form-1099a.pdf) (1 page). Use one file at a time as shown below.

1. [] Open the [CU Studio prebuilt-analyzer gallery](https://contentunderstanding.ai.azure.com/discover). Select the document prebuilt named in each row, choose your resource if prompted, upload the indicated PDF, and run analysis.
2. [] Inspect the document and the actual response together. Click a returned field or table value to inspect its source; compare layout-only output with domain-specific extraction.

| Prebuilt in Studio | Upload | Inspect |
|:---|:---|:---|
| Document Layout | [towing-invoice.pdf](../data/step1/towing-invoice.pdf) | Text, reading order, tables, and page structure. This is not invoice-domain extraction. |
| Invoice | [Same towing-invoice.pdf](../data/step1/towing-invoice.pdf) | Vendor, customer, charges, total, tax, and line items. A charge is not proof of payment. |
| Generic ID Document | [demo-id.pdf](../data/step1/demo-id.pdf) | Named holder and available ID-like fields. This fictional membership specimen is not a government ID. |
| US tax (Form 1099-A) | [form-1099a.pdf](../data/step1/form-1099a.pdf) | Tax year, lender, borrower, account, and form boxes. Nested year/copy results are not extra input documents. |

> [!Note] **Checkpoint:** you can explain the difference between document layout and schema-based extraction.

**Workbench:** do not launch it yet. You will explicitly launch the separate app in [step 5](#step-5-connect-to-your-separate-insurance-workbench-app).

===

## Step 2: Build a custom repair extractor

> [!Note] **Upload from `data\step2`:** [repair-estimate.pdf](../data/step2/repair-estimate.pdf) (1 page). This is the same repair estimate used on page 3 of the core packet in the next steps.

1. [] Move from **Discover** to **Build** in [CU Studio](https://contentunderstanding.ai.azure.com/build) and select **Create** to open the project creation dialog.
2. [] Choose a Preview **Standard Extraction** project. Keep the preconfigured model and other settings unchanged, then select **Create** to create the project.
3. [] Open your new project and select **Browse for Files**. In File Explorer, navigate to C:\Users\LabUser\Desktop\ignite26-LAB664\data\step2 and upload [repair-estimate.pdf](../data/step2/repair-estimate.pdf). In the template selection pop-up that appears, select **Invoice**, then select **Save**.
4. [] Keep the template fields. Add **only these three lowercase fields**, with method **Extract**, and enable source and confidence for them. Do not add separate make/model/year, plate, or odometer-unit fields.

| Field | Type / method | Copy this description |
|:---|:---|:---|
| `vehicle` | String / Extract | Printed vehicle name as one string, including year/make/model when present. Do not add color, decode the VIN, or infer missing details. |
| `vin` | String / Extract | Exact value explicitly labeled VIN. Do not correct it or substitute registration, plate, or account numbers. Leave unset if absent. |
| `odometer` | Number / Extract | Printed Odometer or Inspection Mileage as a number. Remove grouping separators; no units. Do not substitute Annual Mileage or infer an absent value. |

5. [] Select **Save** and wait until saving indicators clear, then select **Run analysis**. Test in Studio before building the analyzer.
6. [] Check the values and source highlights: `vehicle = "2019 Toyota Corolla LE"`, `vin = "5YFEPMAE3KA513905"`, `odometer = 94360`. The repair proposal total is $1,310.13, distinct from the towing invoice. Missing values must not become invented values or zero.
7. [] After the test passes, **Build analyzer** with your own unique ID, for example `lab664_lee_repair`. Record the actual ID and verify the saved schema contains the three fields above. Do not overwrite another learner's analyzer.

### Add a Statement extractor

8. [] Return to **Build** and select **Create**. Select the **Preview** API version, then choose **Standard Extraction**. Keep the preconfigured model and other settings unchanged, then select **Create** to create the second project.
9. [] Open the new project and select **Browse for Files**. Navigate to C:\Users\LabUser\Desktop\ignite26-LAB664\data\documents\packet-01 and upload [06-handwriting.pdf](../data/documents/packet-01/06-handwriting.pdf).
10. [] In the pop-up that appears after the document upload, disable **AI field suggestions**, then select **Save**.
11. [] In the field-schema toolbar, choose **Import**, navigate to C:\Users\LabUser\Desktop\ignite26-LAB664\data\step2, and select [statement-schema.json](../data/step2/statement-schema.json). Confirm schema replacement if prompted, then **Save**. This imports the fields and descriptions; no field-by-field typing is needed.

After import, verify **seven flat fields: five Extract and two Generate**, with **Source & Confidence** enabled. `incident_date` is **Date**; the other six fields are **String**. Use the table below to validate the import; do not add these fields again.

| Field | Type / method | Validate after import |
|:---|:---|:---|
| `claimant_name` | String / Extract | Name explicitly identifying the claimant or insured vehicle owner. Do not substitute a witness, other driver, adjuster, or recipient. Leave unset if unclear. |
| `incident_date` | Date / Extract | Date the reported incident occurred, not the date the statement or email was written or sent. Leave unset if absent. |
| `incident_location` | String / Extract | Location explicitly reported for the incident. Leave unset if absent. |
| `vehicle` | String / Extract | Claimant vehicle as one string, including year, make, model, and trim when stated. Do not include color or the other vehicle. |
| `vin` | String / Extract | Exact VIN explicitly stated for the claimant vehicle. Do not decode, correct, or infer it; leave unset if absent. |
| `reported_damage` | String / Generate | A concise synthesis of claimant-reported damage, combining mentions without inventing damage or presenting it as inspected or verified. |
| `summary` | String / Generate | A concise synthesis of the reported narrative, preserving uncertainty without inferring fault, coverage, liability, or payment. |

12. [] Wait until saving indicators clear, then select **Run analysis** to test the uploaded handwritten statement. Inspect the returned facts alongside the source document. If a fact is not stated in the document, check that the analyzer leaves the corresponding field empty rather than guessing a value.
13. [] Select **Browse for Files**, navigate to C:\Users\LabUser\Desktop\ignite26-LAB664\data\samples, and upload [email-statement.pdf](../data/samples/email-statement.pdf). Run analysis again. In the email, check `claimant_name = "Danielle Ortiz"` and `incident_date = 2026-02-12`, not the email's sent date. The five Extract fields contain stated facts; the two Generate fields provide readable, grounded synthesis rather than verbatim quotes. Inspect source highlights and confidence where returned; for generated text, they support the synthesis rather than prove every word is quoted. If a fact is not stated in the document, check that the analyzer leaves the corresponding field empty rather than guessing a value.
14. [] After reviewing both documents, **Build analyzer** with a unique ID such as `lab664_lee_statement`; record the actual `..._statement` ID for step 4.

> [!Note] **Checkpoint:** tested custom repair and Statement analyzers are ready, and you have both analyzer IDs.

**Workbench:** no app launch is needed here; [step 5](#step-5-connect-to-your-separate-insurance-workbench-app) connects the finished routed analyzer.

===

## Step 3: Classify and split a packet, without extraction

> [!Note] **Start with `data\step3`:** [classification-packet.pdf](../data/step3/classification-packet.pdf) (3 pages). Then use [packet-01.pdf](../data/step3/packet-01.pdf) (Danielle, 13 pages) and [packet-03.pdf](../data/step3/packet-03.pdf) (12 pages) for realistic logical-document boundaries.

1. [] Return to the **Build** tab in [CU Studio](https://contentunderstanding.ai.azure.com/build) and select **Create** to create another project. Set **API Version** to **2026-06-01 (Preview)**, **Workflow kind** to **Classification**, and the model to **GPT-5.5**, then select **Create**. Add the four category keys and descriptions below. **Do not assign child analyzer IDs yet.** The [prebuilt-analyzer gallery](https://contentunderstanding.ai.azure.com/discover) will be used for extraction routes in step 4, not this classification-only test.
2. [] Enable segmentation and choose **Auto segment content**. Leave **Allow in-page segments** off. Do not choose **Segment by page**; keep parent content. The settings are `enableSegment=true`, `allowInPageSegments=false`, `segmentPerPage=false`, `omitContent=false`.

| Category key | Copy this description |
|:---|:---|
| `id_document` | The lab's identity-like demo card with named holder, portrait and membership identifier. This synthetic membership card demonstrates ID field extraction, not government-ID authenticity. Exclude invoice, tax and repair documents. |
| `tax_1099a` | An IRS Form 1099-A Acquisition or Abandonment of Secured Property, including fictional borrower-copy examples. Exclude other tax forms and prose references. |
| `repair_estimate` | A standalone repair workshop estimate or quote with vehicle details and proposed parts/labor. Keep continuation pages of the same estimate together; split a different estimate even if adjacent. Exclude towing/rental/glass invoices and their supporting inspection supplements even when they mention a proposed repair schedule. |
| `other` | Each distinct supporting document: policy declarations/endorsements, claim intake forms, incident reports, handwritten statements, towing/rental/glass invoices with their own continuation supplements, valuation/downtime schedules, and workshop inspection records. Identify logical boundaries even when adjacent documents both have category other. Keep paginated continuation pages together; do not merge different document titles or identifiers. These documents are unrouted, not discarded. |

3. [] Upload the [three-page core](../data/step3/classification-packet.pdf). Save and **Run analysis before building**. Expect ID on page 1, 1099-A on page 2, and repair estimate on page 3. Every page should be covered once. Domain extractor fields are not expected yet.
4. [] Test [packet-01.pdf](../data/step3/packet-01.pdf), then [packet-03.pdf](../data/step3/packet-03.pdf). Inspect the category and page range of each logical document, not one segment per page. Compare to the individual source PDFs under `data\documents\packet-01` and `data\documents\packet-03`. Different adjacent Other documents must remain separate; a document's continuation pages should stay together.
5. [] For packet 01, the authored groups are: membership card p1; policy p2-4; claim p5-6; incident p7; repair p8; statement p9; rental invoice p10-11; inspection p12; 1099-A p13. At this four-class stage, both the statement and rental invoice belong to Other. Review discrepancies rather than assuming authored grouping proves the model wrong.
6. [] After testing, build a unique `..._classifier` analyzer if you want to call this stage from the app. Keep the editable project for step 4.

> [!Note] **Checkpoint:** you have categories and logical page ranges, but no extraction routes.

**Workbench:** [step 5](#step-5-connect-to-your-separate-insurance-workbench-app) explains launching the separate app; it accepts a ready classification-only analyzer as well as a routed one.

===

## Step 4: Add extraction routes to the classifier

> [!Note] **Use the same inputs from `data\step4`:** [classification-packet.pdf](../data/step4/classification-packet.pdf), [packet-01.pdf](../data/step4/packet-01.pdf) (statement and rental invoice), and [packet-03.pdf](../data/step4/packet-03.pdf) (towing invoice). This makes the before/after comparison about routing, not a changed source.

1. [] Reopen your step 3 project in [CU Studio Build](https://contentunderstanding.ai.azure.com/build). Keep the classifier on **GPT-5.5** and the same logical-segmentation settings. Link the first three categories below to the indicated analyzers. Select prebuilts from the [prebuilt-analyzer gallery](https://contentunderstanding.ai.azure.com/discover); use your actual custom repair ID.
2. [] Add `statement`, `towing_invoice`, and `rental_invoice`, using the descriptions below. Route Statement to your custom `..._statement` analyzer and both invoice categories to Invoice. Update Other's description to the new version. Keep both custom extractors on **GPT-5.5**. The resource's `prebuilt-analyzer-completion` mapping must use **GPT-5.2**; verify with the lab owner rather than changing a shared mapping.

| Category key | Extraction route | Description change |
|:---|:---|:---|
| `id_document` | `prebuilt-idDocument.generic` | Keep the step 3 description. |
| `tax_1099a` | `prebuilt-tax.us.1099A` | Keep the step 3 description. |
| `repair_estimate` | Your `..._repair` ID | Keep the step 3 description. |
| `statement` | Your `..._statement` ID | A handwritten or typed claimant statement or email describing the incident, claimant vehicle, and reported damage. Keep continuation pages of the same statement together. Exclude claim forms, incident reports, witness or other-driver accounts, and repair or invoice documents. |
| `towing_invoice` | `prebuilt-invoice` | A towing or roadside-recovery invoice, bill or charge ledger for vehicle transport, storage or release. Keep continuation and release/custody supplements from the same bill together. Payment may be unpaid or pending; do not infer payment. Exclude repair estimates, rental billing, and glass or panel service quotes. |
| `rental_invoice` | `prebuilt-invoice` | A vehicle rental billing document or invoice with rental agreement references, dates or daily charges. Keep the same agreement's pickup/billing/vehicle-condition continuation pages together. Payment may be unpaid or pending; do not infer payment. Exclude towing bills, repair estimates, and glass or panel service quotes. |
| `other` | **No route** | Each distinct unrouted supporting document: policy declarations/endorsements, claim intake forms, incident reports, glass/panel service supporting records, valuation/downtime schedules, and workshop inspection records. Statements, towing bills, and rental billing belong to their named categories, not Other. Identify logical boundaries even when adjacent documents both have category other. Keep continuation pages together; do not merge different titles or identifiers. These documents are unrouted, not discarded. |

3. [] Save and **Run analysis in Studio before building**, first on the core packet and then on both full packets. Compare categories and ranges with step 3, now with child fields and source highlights. Statement, rental, and towing have moved out of Other; other logical boundaries should remain meaningful.
4. [] For the core packet, inspect ID p1, nested tax fields p2, and the three custom repair fields p3. For packet 01, inspect repair p8, the native Statement route on p9, and rental p10-11. Inspect the towing invoice in packet 03. Keep reported statement details distinct from verified facts, and the proposed repair amount distinct from actual invoiced charges.
5. [] Only after review, **Build analyzer** with a new unique `..._router` ID. This is the ready seven-category demo router; do not overwrite the classification-only analyzer. Wait for status **ready** and record this exact ID and the resource endpoint for step 5.

> [!Note] **Checkpoint:** a tested, ready router links every non-Other category to extraction.

**Workbench:** now follow [step 5](#step-5-connect-to-your-separate-insurance-workbench-app) to install and explicitly launch the separate app.

===

## Step 5: Connect to your separate Insurance Workbench App

> [!Note] **App input:** all ten full PDFs in `data\packets` (120 pages total). The app loads these automatically; no manual upload is needed. The completed native results in `data\results` let you explore without submitting analysis. [CU Studio Build](https://contentunderstanding.ai.azure.com/build) remains your authoring tool; the [prebuilt-analyzer gallery](https://contentunderstanding.ai.azure.com/discover) remains in Studio.

### Install once, then launch the app yourself

Install **Python 3.10 or later** with pip and venv. Open PowerShell in the repository root (the folder containing `src`, `data`, and `infra`). Run the setup script. It installs a supported Node runtime if needed, Azure CLI if missing (using Windows App Installer/winget), the locked npm dependencies including **Deep Chat**, and the **Python Agent Framework** dependencies in `.tools\policy-venv`. An internet connection and any installer approval are required. It does **not** sign you in, create cloud resources, or launch the app.

After pulling updates, stop the app, rerun setup, and restart it. The launcher selects the local Python environment automatically. Agent Framework is installed through pip, not npm; its core and OpenAI packages have independent version numbers. For package mirrors or an explicit Python path, see [infrastructure setup](../infra/README.md#lab-machines-with-package-mirrors).

```PowerShell
powershell -ExecutionPolicy Bypass -File .\infra\setup.ps1

# YOU now launch the separate app. Keep this terminal open.
powershell -ExecutionPolicy Bypass -File .\infra\launch-workbench.ps1
```

Open [Insurance Workbench App - http://127.0.0.1:8791/](http://127.0.0.1:8791/) in another browser tab. Do not open `workbench.html` directly. Stop the app with **Ctrl+C**. This lab guide can remain open independently of the app.

### Explore the included results first - no Azure analysis on load

1. [] In **Parse and extract**, select **Load cached results** to load the included completed **10/10** run. The Cached badge identifies historical native CU JSON, not a fresh run or your new analyzer. Its tooltip preserves the original analyzer, API version, timestamp, and dataset fingerprint. Results, fixed extraction checks, and matching saved LLM Agent and policy reviews load together before the table appears. Loading the cache or opening either check view makes no paid model calls.
2. [] Start with **Classification**. Each row is one customer; each check is a returned document instance and page range. Click a check or field value to open its full source PDF at that page. Other is hidden from this grid, not removed from the response.
3. [] Switch to **ID**, **1099-A**, **Repair Estimate**, **Statement**, **Towing Invoice**, and **Rental Invoice**. Only returned types appear. Repair defaults show vendor, vehicle, VIN, total, tax, and line items; use **All fields** for odometer. Statement shows returned fields from its seven-field schema with native source and confidence; unstated values are not invented, and globally empty columns are hidden.
4. [] Turn on **Confidence** to inspect returned scores. Blank means the service omitted a score, not zero. Click line items for source boxes or their table icon to expand item rows below the customer. Click a subfield to highlight its source while keeping the rows open. Drag column edges or the PDF divider to resize. Double-click a field to focus at 300%; double-click again to fit. Use wheel zoom, drag-to-pan, and the bottom page controls.
5. [] Use **{ }** to download the complete native JSON for the selected customer. Compare it with the source PDF; values, geometry, and confidence come from CU, not fabricated app output.

### Compare policy review with and without retrieval

Use the top-level tabs to move between **Parse and extract**, **Check consistency**, and **Check policies**. **Check consistency** validates returned fields, arithmetic, and cross-document consistency. **Check policies** uses an agent and retrieved policy evidence for five rental-processing checks. Neither changes the other's results. Selecting a policy check opens its finding and claim-versus-policy values in the right panel. Select a linked value to inspect its source PDF, then **Back to policy check** to return. The loaded CU results remain shared across tabs.

On first launch, select **Check policies** > **FoundryIQ** > **Load cached results**. The app loads the included CU run automatically; loading extraction results separately isn't required. Without compatible local reviews, the app reads all ten synthetic reviews directly from the checked-in bundle. No Azure setup, credentials or restore command is needed. The **Bundled demo** label identifies the original index and read-only results; local configuration and caches aren't overwritten. Follow-up chat isn't available for bundled results. The lab owner must complete [policy setup](../docs/policy-setup.md) for live work. Sign in with `az login` using your approved lab identity only when running live work.

1. [] In **Check policies**, select **FoundryIQ**, then **Load cached results** for the included **10/10** CU run and **50** saved policy checks. Alternatively, start with **Parse and extract** > **Load cached results**. Loading makes no Azure calls.
2. [] To request live policy work, select **Run live** and confirm the operation for all loaded cases. The status banner names the active packet and shows elapsed time. Each uncached packet gets one Search prefetch and five parallel Agent Framework calls, one per check. Missing claim fields can require one additional whole-packet CU extraction. Azure charges apply.

   Keep the tab open; refresh the same tab to resume progress rather than starting another run. Matching current reviews load from cache without another model call. **Run live** isn't a force-refresh button.
3. [] Optionally select **No policy retrieval** to inspect a saved baseline if available, then return to **FoundryIQ**. Changing the dropdown alone doesn't submit a new run.
4. [] Inspect **Daily cost**, **Rental dates**, and **Active policy**, followed by **Covered charges** and **Payment approval**. A check mark means **Satisfied**; an open circle means **Review required**. The circular-arrow **Waiting for info** status means missing claim evidence or approval, not a model still running. **N/A** identifies a check that doesn't apply.

| Case | CU daily base | Contractual daily cap | Retrieved SOP routine authority | Included saved daily-cost result |
|:---|---:|---:|---:|:---|
| Packet 01 / Texas | $54 | $85 | $75, inclusive | **Satisfied**: $54/day and four billed days fit the contractual limits |
| Packet 02 / Washington | $61 | $85 | $60, inclusive | **Satisfied**: $61/day and five billed days fit the contractual limits; payment authority is separate |

In the refreshed saved reviews, both packets show **Waiting for info** for rental dates and insurer approval. Packet 02's **Covered charges** requires review because its local rental levy needs supporting evidence. These saved results are model-generated, not scripted outcomes.

5. [] For packet **01**, select the Texas **Source** link. Inspect **TX-R2** on page 2 and **Schedule A** on page 3 of `tx-rental-review-sop-v2.pdf`. The $75 value is internal routine handling authority, not the $85 contractual cap. Blank cells in the exception table don't grant extra authority. Also inspect the matching revised declarations, rental terms/diagram and issued amendment. The blank optional-code cell must not shift the Honda's deductible or rental limits.
6. [] In the source viewer, compare **Document**, **CU Search** and **Digital parse**. CU Search uses `prebuilt-documentSearch` and its own analyzer-keyed cache, not relabeled Layout output. Select **Back to policy check** to restore the finding. Optionally inspect Washington's scanned SOP or Arizona's image-based eligibility flowchart. A missing extraction has an explicit billable generation action; switching tabs alone doesn't call CU.
7. [] Select **Ask agent** in the right panel and ask, "Explain this case's daily-rate result. Cite the SOP and distinguish routine authority from the contractual cap." Chat uses the selected case and mode without replacing its saved checks; each submitted question can incur Azure charges.

These are source-based examples, not guaranteed model answers. Inspect differing results, missing facts or errors rather than forcing a pass. The SOP cannot supply a missing contractual benefit. Missing actual repair dates or pending insurer approval produce **Waiting for info**; contradictory evidence or unclear controlling rules require review. An issued amendment and its effective time, not a customer signature alone, establish changed terms. **Satisfied** for daily cost doesn't approve the claim or authorize payment.

### Optional: inspect Search, policy files and the agent

| Inspect | Where to look | What to learn |
|:---|:---|:---|
| Active Search index | Note the index below **Policy retrieval**. In the [Azure portal](https://portal.azure.com/), open the Search resource matching `searchEndpoint` in `.tools\policy-agent-framework.json`, then **Indexes** > the active index > **Search explorer**. Search `rental daily rate`. | Chunks carry policy text, document identity, version and page information. The agent filters to the loss state and verified source generation. |
| Original policy files | Open the [v2 corpus](../data/policies/rental/ocr-comparison-v2/), especially the [Texas SOP](../data/policies/rental/ocr-comparison-v2/tx-rental-review-sop-v2.pdf) and [manifest](../data/policies/rental/ocr-comparison-v2/manifest.json). | CU must preserve table structure, blank cells, scanned text and figures so rules can be retrieved and cited. |
| Blob ingestion, if deployed | In Search, inspect the matching **Data source**, **Indexer** and **Skillset**. Follow the actual container to the storage account's **Storage browser**. | Managed ingestion reads policy PDFs from Blob Storage, runs the CU skill and indexes chunks. The Layout index alone doesn't prove this pipeline exists. |
| Agent Framework | Open [`infra/policy-framework-agent.py`](../infra/policy-framework-agent.py). Find `Agent`, `OpenAIChatClient` and `search_policy_rules`. | Initial reviews use five parallel calls with relevant CU fields and prefetched rules; follow-up chat can use the Search tool. |

For shared-resource names and subscriptions, see [under the hood](../docs/policy-checks.md#optional-look-under-the-hood). Don't change roles, networking or shared resources during this exercise.

**FoundryIQ** is the lab's umbrella label for grounded retrieval. This implementation queries an ordinary Azure AI Search index directly, not a Foundry IQ knowledge base. Read the actual extraction label: the configured shared index uses **CU Layout**. The optional [managed CU pipeline](../docs/policy-setup.md) provides semantic extraction only after successful setup. **CU Search** and **Digital parse** document tabs are separate cached representations; changing the viewer doesn't change the active Search index.

### Connect your own built analyzer and run live

Stop the app first. Sign in with Azure CLI; browser Studio sign-in does not authenticate this Node app. Choose the subscription containing **your approved CU resource**. Use its resource-root endpoint, not a Studio or Foundry project URL. Your Azure identity needs permission to list and invoke CU analyzers and to invoke the configured Azure GPT deployments used by packet checks.

```PowerShell
az login
az account set --subscription "YOUR-SUBSCRIPTION-ID"

powershell -ExecutionPolicy Bypass -File .\infra\launch-workbench.ps1 `
  -Endpoint "https://YOUR-APPROVED-RESOURCE.services.ai.azure.com"
```

1. [] Reopen or reload [Insurance Workbench App](http://127.0.0.1:8791/). In **Analyzer**, select the exact `..._router` ID you built in step 4. The list contains ready custom logical classifiers/routers, not standalone prebuilts. If missing, check the endpoint, permissions, API version, and that the analyzer was built successfully.
2. [] Click **Run live**. Read the confirmation for ten packets / 120 pages; only confirm when you intend to incur Azure charges. The app submits each packet once to the selected ready router and uses its linked extraction routes. It does not create analyzers, deploy models, or add a separate Statement pass.
3. [] Watch progress and elapsed time. Each native response is saved under `data\results\RUN-ID` before results are derived. The live batch then runs fixed checks and automatically caches LLM Agent review for failed findings, reusing an existing matching review when available. Both packet analysis and uncached LLM Agent review can incur Azure charges. Completed results become a new cache entry. A failed run remains visibly failed; inspect its error before explicitly starting another billable run.
4. [] Compare your live extraction with the PDFs and the saved run. To see classification alone, select your step 3 `..._classifier` and explicitly start a separate billable run. Fields appear only when extraction routes actually returned them.

> [!Note] **Checkpoint:** you connected CU results to a separate application, compared policy checks with and without retrieval, and traced a daily-rate result to its SOP.

### Extraction checks, LLM Agent review, and targeted reruns

1. [] Select the **Check consistency** pivot to compare all customers in the same grid. Two-line check names have full descriptions in tooltips. **Primary checks** keep every warning/error across the packets, plus Amount balance and Claimant match; enable **All checks** to reveal the other clean checks. Each cell shows the worst result across the packet's documents: green **Pass**, yellow **Warn** for not-checkable evidence, or red **Error**. Amount balance compares subtotal + tax with total; optional discount/deductible fields are ignored. The live batch automatically caches LLM Agent reviews for failed findings. Cache Results loads these saved reviews; passing checks have no LLM review.
2. [] Click a cell for a compact table of source documents, specific problems, and **LLM Agent review** badges: **Extraction issue** or **Document issue**. These are advisory diagnoses, not proven causes. Click a problem or document to highlight its source at full page width; missing values show available context rather than an invented box. Open a review badge for reasoning, suggested action, a field/value table, and model/cache details. **Highlight all values** shows the returned source boxes together; use the page controls when evidence spans pages. Inline details expand vertically, so only the results grid scrolls. Click the cell again or the close icon to collapse it. The service prefers deployed **GPT-6.1 Sol** and falls back to existing **GPT-5.5** only if the primary deployment is missing. **Refresh LLM review** under **Review options** forces fresh paid model calls for all failed findings in this packet. Its temporary review is not saved and never changes policy status or cached reviews.
3. [] Both issue types support **Rerun this document**. For an extraction problem, first update and build the affected extractor in CU Studio. Open the check's review badge, expand **Refine extractor / rerun one document**, and enter the existing or updated analyzer ID. Only that already extracted PDF is submitted, with a fresh Azure call every time. Fresh fields and the selected check's preview result appear inside this policy panel; use **Highlight all values** to inspect their source together. Previews are not cached or saved and disappear when the panel is reopened or Cache Results is loaded again. Original extraction grids, native JSON, policy statuses, and cached reviews stay unchanged. If a split or merged segment cannot be matched to one source PDF, review its boundaries in Studio first.

> [+Note] **Where the files are**
>
> `instructions\lab.md` is the Markdown version of this single guide; `instructions\lab.html` is the original HTML version. `infra\setup.ps1` installs dependencies; `infra\launch-workbench.ps1` launches only the app. `src\workbench` contains the minimal app runtime, not another lab guide.
>
> `data\packets`: 10 complete customer PDFs. `data\documents\packet-01` through `packet-10`: 90 individual logical-document PDFs, extracted from the authored page groups. `data\samples`: six small Studio specimens. `data\packets.json`: source hashes and authored page ranges. `data\results`: one included completed run with its original manifest and ten native JSON responses; future live runs save here too.
>
> `data\step1` through `data\step4` are convenience copies of the recommended inputs, not a second dataset. The app uses the canonical PDFs under `data`. Full packet 01 contains a statement and rental billing; full packet 03 contains towing. The authored four-class reference labels statements and both invoice types as Other, while the seven-class routed run gives them separate categories.

---

All people and documents are synthetic. This lab demonstrates document processing, not government-ID validation, tax advice, coverage determination, liability, payment approval, or an insurance claim decision. A person must review the actual source.
