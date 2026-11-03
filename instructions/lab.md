@lab.Title

## Welcome to Your Lab Environment

To begin, log into the virtual machine using the following credentials: +++@lab.VirtualMachine(Win11-Pro-Base).Password+++

**Note:** Text formatted as an +++example+++ represents type text. Clicking on this text will automatically insert it to prevent any typing errors.

# From documents to an Insurance Workbench

In this lab you will use Azure AI Content Understanding to turn synthetic insurance documents into structured, source-linked results. You will build and test analyzers in CU Studio, then connect your finished analyzer to a **separate Insurance Workbench application**. Along the way, you will:

- **Explore prebuilt analyzers:** compare document layout with pre-built extraction models, and inspect how returned values relate to the source documents.
- **Customize extraction:** extend an invoice template to extract vehicle, VIN, and odometer details from a repair estimate, then build a Statement analyzer that combines extracted facts with grounded summaries.
- **Classify and split document packets:** identify document types and logical page ranges in mixed insurance packets, keeping continuation pages together without extracting fields yet.
- **Add extraction routes:** connect document categories to prebuilt analyzers and your custom repair and Statement analyzers, including dedicated routes for towing and rental invoices. Review the returned fields and source highlights.
- **Review a collection in the Insurance Workbench:** compare document types and extracted fields across ten packets, spot missing or repeated content, and use business consistency checks to investigate suspicious values before exploring policy reviews and live analysis.

===

## Step 1: Explore prebuilt analyzers

To get started, let's explore the prebuilt analyzers in CU (Content Understanding) Studio by uploading and analyzing a few sample documents.
This will help you understand the distinction between layout extraction and schema-based extraction before you move on to customizing your own analyzers.

Open the browser to navigate to CU the Studio Gallery (`https://contentunderstanding.ai.azure.com/discover`).
Click **Sign in** on the top right corner of the page and log in with the provided credentials for Azure:
- Username: +++@lab.CloudPortalCredential(User1).Username+++
- If prompted for a Temporary Access Pass (TAP): +++@lab.CloudPortalCredential(User1).AccessToken+++
- If prompted for a Password: +++@lab.CloudPortalCredential(User1).Password+++

Once done, follow the steps below to explore the prebuilt analyzers:
1. Click on **Layout** to test the document layout extraction. When prompted to confirm the details of the subscription, resource group and resource name, confirm default selections and proceed. Click **Next**->**Save**.
2. You'll get a list of samples for different content types (checklist, financial report, formulas, etc). Select a sample to see the original document scan and how the prebuilt analyzer extracts information from it.
!IMAGE[chshn4cn.png](instructions359897/chshn4cn.png)
4. Next click on **Browse for files** to upload your own document for analysis. In the File Explorer window that opens, navigate to `C:\Users\LabUser\Desktop\ignite26-LAB664\data\step1` and select **towing-invoice.pdf**. Notice how both the content and the format (tables, lists, headers) are extracted and displayed on the right side panel.
!IMAGE[xfe4ei8u.png](instructions359897/xfe4ei8u.png)

Now come back to the previous page - by clicking on the arrow on the top left corner of the page - and let's examine the differences between the prebuilt layout extraction and the schema-based extraction for the same document. 
1. Scroll down on the **Procurement** section to locate the **Invoice** prebuilt analyzer and click on it to open the details.
2. Inspect the default sample to understand how the schema-based extraction identifies and extracts specific fields relevant to the document type, such as **AmontDue**, **BalanceForward** and **Billing Address**. Note that each field is also mapped to the corresponding confidence score.
3. Now upload the same **towing-invoice.pdf** document to see how the schema-based extraction applies to your own file. Compare the extracted fields and confidence scores with the layout extraction results you've got in the previous step to understand the differences.

Feel free to experiment with further pre-built analyzers to understand how CU Studio handles different document types and extraction scenarios. Below you can find a few examples of prebuilt analyzers along with the sample documents provided in the data folder, and the fields they extract.

| Prebuilt in Studio | Upload | Inspect |
| :--- | :--- | :--- |
| Identity / Generic ID document | demo-id.pdf | Named holder and available ID-like fields. This fictional membership specimen is not a government ID. |
| US tax / 1099A | form-1099a.pdf | Tax year, lender, borrower, account, and form boxes. Nested year/copy results are not extra input documents. |

> [!Note] **Checkpoint:** you can explain the difference between document layout and schema-based extraction.

===

## Step 2: Build a custom repair extractor

In the following step, we will build a custom repair extractor to handle repair estimate documents specifically. This involves creating a new extraction project, defining the necessary fields, and testing the extraction on a sample repair estimate PDF.

For this step, use the **gpt-5.5** model instance pre-provisioned and mapped by the lab template. 

1. Move from the **Discover** to the **Build** tab, by selecting it on the top right corner of the blue top navigation bar.
2. Click on **Create** to start building your custom repair extractor.
3. Name the project as `custom-repair-extractor`.
4. Select `2026-06-01 (Preview)` as the API version and `Standard Extraction` as the workflow type.
!IMAGE[kke6gm3z.png](instructions359897/kke6gm3z.png)
6. Expand the **Advanced settings** section and select **gpt-5.5** as model.
7. Leave the other parameters as default and confirm by selecting **Create**.
!IMAGE[qm5a1m18.png](instructions359897/qm5a1m18.png)
7. Once your project is created, select **Browse for Files** and upload `C:\Users\LabUser\Desktop\ignite26-LAB664\data\step1\repair-estimate.pdf`. **Run analysis**.
8. In the **Choose a template window**, select the **Invoice** one. Click on **Save** to proceed.
9. Add **these three lowercase fields**, with method **Extract**, one by one. For each field, enter the field's **Name** and **Description** from the table below. Complete both cells before selecting **Add field** again, and repeat for all three rows.

| Field | Type / method | Copy this description |
| :--- | :--- | :--- |
| `vehicle` | String / Extract | `Printed vehicle name as one string, including year/make/model when present. Do not add color, decode the VIN, or infer missing details.` |
| `vin` | String / Extract | `Exact value explicitly labeled VIN. Do not correct it or substitute registration, plate, or account numbers. Leave unset if absent.` |
| `odometer` | Number / Extract | `Printed Odometer or Inspection Mileage as a number. Remove grouping separators; no units. Do not substitute Annual Mileage or infer an absent value.` |
10. Click on **Save** to confirm the added fields.
!IMAGE[y1l65rn4.png](instructions359897/y1l65rn4.png)
11. **Run analysis**.
!IMAGE[ctdjrztc.png](instructions359897/ctdjrztc.png)
12. In the analysis results, verify the saved schema contains the three fields above: `vehicle = "2019 Toyota Corolla LE"`, `vin = "5YFEPMAE3KA513905"`, `odometer = 94360`. The repair proposal total is $1,310.13. 
13. After the test passes, click on **Build analyzer** and name it `repair_extractor_analyzer`. Add as description `Extractor for repair estimates based on uploaded documents`.Select **Build** to complete the process.
!IMAGE[eli9ysmu.png](instructions359897/eli9ysmu.png)
14. Once you are prompted with 'Built successfully', your analyzer is ready for use. Click on **Jump to analyzer list** to verify the analyzer details. You'll find your newly created analyzer in the **Analyzer list**.
!IMAGE[22c2gk9p.png](instructions359897/22c2gk9p.png)

### Add a custom Statement extractor

Now let's work with a different kind of document: a claimant's account of an incident. Unlike an invoice, a statement may describe the same damage in several places or leave important details unstated. You will use **Extract** for facts explicitly present in the document and **Generate** for a concise, grounded synthesis of the narrative.

Instead of entering each field manually, you will import a prepared schema and inspect how its field descriptions constrain the result.

1. Return to the **Build** tab -> **Project list** and create a second **Standard Extraction** project using the '2026-06-01 (Preview)' API version. Name it `custom-statement-extractor`.
2. In **Advanced settings**, select **gpt-5.5**, then select **Create**.
3. Click on **Browse for Files**. Within the File Explorer window, navigate to `C:\Users\LabUser\Desktop\ignite26-LAB664\data\documents\packet-01` and upload `06-handwriting.pdf`.
4. In the pop-up that appears after the document upload, keep **Document Analysis** as selected template, disable **AI-Powered field suggestions**, then select **Save**.
!IMAGE[szpjguew.png](instructions359897/szpjguew.png)
5. In the field-schema toolbar, choose **Import**, navigate to `C:\Users\LabUser\Desktop\ignite26-LAB664\data\step2`, and select `statement-schema.json`. Confirm schema replacement if prompted, then **Save**. This imports the fields and descriptions; no field-by-field typing is needed.
!IMAGE[03cudcq2.png](instructions359897/03cudcq2.png)

You should have **seven flat fields: five Extract and two Generate**, with **Source & Confidence** enabled. *Do not add these fields again*.

| Field | Type / method | What to check |
| :--- | :--- | :--- |
| `claimant_name` | String / Extract | Identifies the claimant or insured vehicle owner, not a witness, other driver, adjuster, or recipient. |
| `incident_date` | Date / Extract | Uses the incident date, not the date the statement or email was written or sent. |
| `incident_location` | String / Extract | Contains only an explicitly reported incident location. |
| `vehicle` | String / Extract | Describes the claimant's vehicle as one string, without color, the other vehicle, or inferred details. |
| `vin` | String / Extract | Preserves the exact stated VIN without decoding, correcting, or inferring it. |
| `reported_damage` | String / Generate | Combines claimant-reported damage into a concise description, without presenting it as inspected or verified. |
| `summary` | String / Generate | Summarizes the narrative while preserving uncertainty, without inferring fault, coverage, liability, or payment. |

6. Wait until saving indicators clear, then select **Run analysis** to test the uploaded handwritten statement. Inspect the returned facts alongside the source document.
   - In the statement, check `claimant_name = "Danielle Ortiz"` and `incident_date = 2026-02-12`. The incident date should not be replaced by the letter's sent date.
   - The five *Extract* fields contain stated facts; the two *Generate* fields provide readable, grounded synthesis rather than verbatim quotes.
   - Inspect source highlights and confidence where returned. 
   - If a fact is not stated in the document, check that the analyzer leaves the corresponding field empty rather than guessing a value.

> [!Tip] 
> Make sure to disable the **Hide missing fields** toggle to view all fields, including those that are not populated in the current document.
>
> !IMAGE[33b9kcoj.png](instructions359897/33b9kcoj.png)

Next, test the same schema against a typed email:

1. Select **Browse for Files** and upload `C:\Users\LabUser\Desktop\ignite26-LAB664\data\samples\email-statement.pdf`. Save the project, wait for saving to finish, then select **Run analysis**.
2. Perform the same checks as in the handwritten statement. 
3. After reviewing both documents, select **Build analyzer** and enter a new unique ID, for example `statement_extractor_analyzer`. Add as a description `Custom analyzer for extracting facts from handwritten and typed statements.` In the **Analyzer list**, you should now see two custom analyzers, as in the screenshot below.
!IMAGE[516v1pe7.png](instructions359897/516v1pe7.png)

> [!Note] **Checkpoint:** your custom repair and statement analyzers have both been tested and built, and you have recorded both analyzer IDs.

===

## Step 3: Classify and split a packet, without extraction

So far, you have analyzed one document at a time. An insurance submission usually contains several documents, often with different formats and multiple pages. In this step, you will create a classifier that identifies document types and splits a packet into logical documents before extracting any fields.

You will start with a small three-page packet, then test the same configuration against two larger packets. This will help you see the difference between a page boundary and a document boundary.

### Create the classification project

1. Return to **Build**->**Project List** in CU Studio and create a new **Classification** project, named `packet_classifier`. Make sure to configure the API version to *Preview* first.
!IMAGE[9maoqxjx.png](instructions359897/9maoqxjx.png)
2. In **Advanced settings**, select **gpt-5.5** as **Model for Analysis** and create the project.
3. In the new project, select **Browse for files**. Navigate to `C:\Users\LabUser\Desktop\ignite26-LAB664\data\step3` and upload `classification-packet.pdf`.
 
> [!Note] **Upload first:** the routing-rule editor becomes available after a file is uploaded.

4. In **Routing rules**, add the four category keys and descriptions in the table below, one by one. For each category, enter the category's **Name** and **Description** from the table. Keep the keys exactly as shown. Complete both cells before selecting **Add category** again, and repeat for all four rows.
!IMAGE[7qhnpb5o.png](instructions359897/7qhnpb5o.png)

> [!Note] **Do not assign child analyzer IDs yet**; you will add extraction routes in step 4.

| Category key | Copy this description |
| :--- | :--- |
| `id_document` | `The lab's identity-like demo card with named holder, portrait and membership identifier. This synthetic membership card demonstrates ID field extraction, not government-ID authenticity. Exclude invoice, tax and repair documents.` |
| `tax_1099a` | `An IRS Form 1099-A Acquisition or Abandonment of Secured Property, including fictional borrower-copy examples. Exclude other tax forms and prose references.` |
| `repair_estimate` | `A standalone repair workshop estimate or quote with vehicle details and proposed parts/labor. Keep continuation pages of the same estimate together; split a different estimate even if adjacent. Exclude towing/rental/glass invoices and their supporting inspection supplements even when they mention a proposed repair schedule.` |
| `other` | `Each distinct supporting document: policy declarations/endorsements, claim intake forms, incident reports, handwritten statements, towing/rental/glass invoices with their own continuation supplements, valuation/downtime schedules, and workshop inspection records. Identify logical boundaries even when adjacent documents both have category other. Keep paginated continuation pages together; do not merge different document titles or identifiers. These documents are unrouted, not discarded.` |

Next, configure how the classifier separates documents:

1. In **Routing rules**, turn on **Enable segment**, then open the settings panel, by clicking on the gear icon. Select **Auto segment content**, leave **Allow in-page segments** off, and do not select **Segment by page**. Close the dialog and leave other settings unchanged.
!IMAGE[9zacnykv.png](instructions359897/9zacnykv.png)

> [!Note] With the configured settings, a two-page rental invoice should remain one logical document. Two adjacent documents should still be separate, even when both belong to `other`.

2. Select **Save** and wait until saving indicators clear before changing tabs. Select **Run analysis** and remain in the project until it finishes. Inspect the results to ensure documents are segmented correctly.
3. Inspect details in **Test** tab. The **Segment** selector initially shows the retained parent, `input1`. Open it and select each `input1/segment...` entry to see its category and page range. Expect `id_document` on page 1, `tax_1099a` on page 2, and `repair_estimate` on page 3. Every page should be covered once. Classification-only child segments have **Result**, not domain extractor fields.
!IMAGE[s51l89mw.png](instructions359897/s51l89mw.png)
4. To keep a before/after comparison, select the parent `input1`, then **Result** and **Download** to save the JSON. 
!IMAGE[n0m86b6w.png](instructions359897/n0m86b6w.png)

> [!Tip] Download results before leaving the project or adding routes; reopening a saved project does not restore the displayed analysis results.

### Test the full customer packet

In the previous step, you tested a small packet to ensure the classifier correctly segments individual documents. Now, you will test the full customer packet to verify the classifier's behavior on larger, multi-document files.

1. Within the same project, select again **Browse for Files** and upload `C:\Users\LabUser\Desktop\ignite26-LAB664\data\step3\packet-01.pdf`. 
2. Click on **Run analysis**. After it finishes, inspect each segment's category and page range. Compare the returned boundaries with the individual PDFs under `C:\Users\LabUser\Desktop\ignite26-LAB664\data\documents\packet-01`. Use the authored document groups below as a reference:

| Pages | Logical document | Category at this stage |
| :--- | :--- | :--- |
| 1 | Membership card | `id_document` |
| 2-4 | Policy | `other` |
| 5-6 | Claim | `other` |
| 7 | Incident report | `other` |
| 8 | Repair estimate | `repair_estimate` |
| 9 | Statement | `other` |
| 10-11 | Rental invoice | `other` |
| 12 | Inspection | `other` |
| 13 | Form 1099-A | `tax_1099a` |

3. Check that continuation pages stay together, while different adjacent documents remain separate even when both belong to `other`. The statement and rental invoice are Other at this stage; they are unrouted, not discarded. Download the parent result for comparison, as you've done in the previous step.

> [!Tip] You can easily check the pages assigned to each segment, by looking at the label below the segment name.
> !IMAGE[vcl16bde.png](instructions359897/vcl16bde.png)

4. Next, upload `packet-03.pdf` from the same folder and run analysis. Review its 12 pages against the individual files in `C:\Users\LabUser\Desktop\ignite26-LAB664\data\documents\packet-03`, then download the parent result. Use the table above as a reference for expected page ranges and categories.
5. Before moving to the next step, select **Build analyzer** and use a unique ID such as `packet_classifier`. Also include a description, for example, `Classifier for multi-document analysis`.
6. After the build succeeds, choose **Stay in the project** to continue.

> [!Note] **Checkpoint:** you can identify categories and logical page ranges in a mixed packet. No extraction routes have been assigned yet.

===

## Step 4: Add extraction routes to the classifier

> [!Note] **Reuse the uploaded packets:** the three PDFs in `data\step4` are identical to the ones in `data\step3`. Select their existing thumbnails in the project. If you need to upload them again, use [classification-packet.pdf](../data/step4/classification-packet.pdf), [packet-01.pdf](../data/step4/packet-01.pdf) (statement and rental invoice), and [packet-03.pdf](../data/step4/packet-03.pdf) (towing invoice). This keeps the before/after comparison about routing, not a changed source.

1. Continue in the editable step 3 project. If you left it, return to [CU Studio Build](https://contentunderstanding.ai.azure.com/build), open **Project list**, and open your project. 
2. Open **Routing rules**. In each existing category's **Analyzer ID** selector, choose the route in the table below. Use the selector's **Prebuilt** tab to search for the exact prebuilt ID, or **Custom** to find your built repair analyzer. Selecting a route shows its schema preview within the project; you do not need to leave for the gallery.
!IMAGE[1b7s3xw7.png](instructions359897/1b7s3xw7.png)

> [!Note] For tax, choose the unversioned `prebuilt-tax.us.1099A`, not the year-specific entry. Edit the existing `other` description to the new version below, but leave its Analyzer ID unassigned. 

| Category key | Extraction route | Description change |
| :--- | :--- | :--- |
| `id_document` | `prebuilt-idDocument.generic` | Keep the step 3 description. |
| `tax_1099a` | `prebuilt-tax.us.1099A` | Keep the step 3 description. |
| `repair_estimate` | Your `repair_extractor_analyzer` ID | Keep the step 3 description. |
| `other` | **No route** | Each distinct unrouted supporting document: policy declarations/endorsements, claim intake forms, incident reports, glass/panel service supporting records, valuation/downtime schedules, and workshop inspection records. Statements, towing bills, and rental billing belong to their named categories, not Other. Identify logical boundaries even when adjacent documents both have category other. Keep continuation pages together; do not merge different titles or identifiers. These documents are unrouted, not discarded. Exclude towing/recovery/security charge supplements; classify those as towing_invoice. |

3. Select **Add category** and enter `statement` with its description below, then select your custom Statement analyzer through **Analyzer ID** > **Custom**. Repeat for `towing_invoice` and `rental_invoice`, selecting `prebuilt-invoice` through **Prebuilt** for each. Complete each name and description before adding the next row.
!IMAGE[ujvd6zg6.png](instructions359897/ujvd6zg6.png)

| Category key | Extraction route | Description change |
| :--- | :--- | :--- |
| `statement` | Your `statement_extractor_analyzer` ID | A handwritten or typed claimant statement or email describing the incident, claimant vehicle, and reported damage. Keep continuation pages of the same statement together. Exclude claim forms, incident reports, witness or other-driver accounts, and repair or invoice documents. |
| `towing_invoice` | `prebuilt-invoice` | A towing or roadside-recovery invoice, bill or charge ledger for vehicle transport, storage or release. Keep continuation and release/custody supplements from the same bill together. Payment may be unpaid or pending; do not infer payment. Exclude repair estimates, rental billing, and glass or panel service quotes. Include towing/recovery/security charge supplements that list service charges or a total due, even when they also contain inspection details or repair-quote references. |
| `rental_invoice` | `prebuilt-invoice` | A vehicle rental billing document or invoice with rental agreement references, dates or daily charges. Keep the same agreement's pickup/billing/vehicle-condition continuation pages together. Payment may be unpaid or pending; do not infer payment. Exclude towing bills, repair estimates, and glass or panel service quotes. |

4. Verify there are **seven categories and six assigned routes**, with no route for `other`. Keep **Enable segment** on and click on the gear icon to verify the settings. Keep **Auto segment content** selected, **Allow in-page segments** off, and **Segment by page** unselected. 
!IMAGE[bj0sbmti.png](instructions359897/bj0sbmti.png)
5. Select **Save** and wait until saving indicators clear.
6. Select the existing **classification-packet.pdf** thumbnail, then **Run analysis**. Wait for completion before inspecting results or selecting another file. 
7. In **Test**, expand the segments dropdown and select the child content you want to inspect (e.g. input1/segment1), then open **Fields**. 
!IMAGE[6cp63e2r.png](instructions359897/6cp63e2r.png)

> [!Note] The parent `input1` is not the child extractor's field view. 

Inspect ID fields on segment 1, nested 1099-A fields on segment 2, and custom `vehicle`, `vin`, and `odometer` fields on segment 3. The tax route adds nested year/copy segment entries; select the nested entry with a **Fields** tab. These are not extra input documents. Select a field label to inspect its source highlight. 
8. Return to `input1` > **Result** and download the routed result separately from the step 3 JSON.
9. Replicate the same process for the other 2 files:
   - Select **packet-01.pdf** and run analysis. Compare categories and page ranges with step 3, then inspect repair on page 8, the Statement route on page 9, and the rental invoice across pages 10-11. The statement and rental invoice now have their named categories and child fields rather than belonging to Other. Check that the rental continuation remains part of the same invoice. Download the parent result.
   - Select **packet-03.pdf** and run analysis. Inspect the Statement route on page 9 and the towing invoice on page 10, along with the other categories and logical boundaries. Check invoice amounts against the towing supplement's **$237 charge**, not the separate **$1,699.04 repair quote** it references. Download the parent result. Other documents remain in the parent content without a domain extraction route.
10. Compare returned fields with their source documents. Keep claimant-reported details distinct from verified facts, and proposed repair amounts distinct from invoiced charges or proof of payment. If a fact is not stated, check that its field is unset rather than invented; turn off **Hide missing fields** to see fields marked **Not found**.
11. After reviewing all three packets, select **Build analyzer** with a new unique ID, such as `router_analyzer`. Do not overwrite the classification-only analyzer you created in the previous step. After a successful build, use **Jump to analyzer list**. Verify this exact analyzer has status **Ready**. Record its ID and your resource endpoint for step 5.

> [!Note] **Checkpoint:** a tested, ready router links every non-Other category to extraction.

===

## Step 5: Setup Insurance Workbench app

In this step, you will move from authoring analyzers to reviewing their results in an application. The Insurance Workbench loads ten customer packets, totaling 120 pages, from `data\packets`; you do not need to upload them manually.

To evaluate an analyzer, run it across a representative collection, not just one sample, and compare the results. You will use saved responses from a real CU run across all ten packets, then apply business consistency checks in step 6. Loading saved results does not submit new analysis. CU Studio remains your tool for editing and building analyzers.

### Prepare and launch the app

Use the prepared lab environment with Azure CLI and **Python 3.10 or later**, including pip and venv. The commands below restore dependencies, discover the lab's existing Azure resources, and index the policy PDFs using Search-managed Standard extraction with figure descriptions. They do not redeploy Azure infrastructure or assign roles.

1. Open **Windows PowerShell** CLI and move to the repository root, the folder containing `src`, `data`, and `infra`:

   ```PowerShell
   Set-Location "C:\Users\LabUser\Desktop\ignite26-LAB664"
   ```

2. Sign in with the account provided in the **Resources** tab. Choose **Work or School account** if prompted, then select the lab subscription:

   ```PowerShell
   az login

   ```

3. Run these two commands in order. Setup restores the locked npm dependencies, including Deep Chat, and prepares `.tools\policy-venv` using the lab's approved package sources. Deployment discovers Search, Storage, Foundry and the model in your resource group, uploads the policy PDFs to Blob Storage, and configures a Search indexer and Content Understanding skill. Azure AI Search runs extraction, semantic chunking and AI figure descriptions, then populates the index. Deployment also prepares the separate claim-summary analyzer and writes the workbench connection after verification. Python does not extract or manually upload policy chunks. No pre-filled configuration file or hosted agent is needed.

   ```PowerShell
   powershell -ExecutionPolicy Bypass -File .\infra\setup.ps1
   powershell -ExecutionPolicy Bypass -File .\infra\deploy.ps1 -ResourceGroup "@lab.CloudResourceGroup(1).Name" -Apply
   ```


4. Launch the separate app and keep this terminal open:

   ```PowerShell
   powershell -ExecutionPolicy Bypass -File .\infra\launch-workbench.ps1
   ```

5. Open +++http://127.0.0.1:8791/+++ in a new browser tab. Do not open `workbench.html` directly.

The app reads the included CU results and historical policy reviews directly from the repository. 

For live policy checks and follow-up chat, complete [Prepare live policy checks](#prepare-live-policy-checks) below before selecting **Run live**.

> [!Note] To stop the app at anytime just return to PowerShell and press **Ctrl+C**. 

### Parse and extract across the collection

1. Open **Parse and extract**, select **Load cached results**, and wait for loading to finish. Confirm the included run is complete: **10/10** packets.
2. In **Classification**, compare document types across rows. Each row is one customer; each check mark is a returned document instance and page range, not an accuracy check. Packet **01** has one repair estimate and a rental invoice; packet **03** has two repair estimates and a towing invoice, but no rental invoice. Select the marks to inspect the source pages.
3. Select **Repair Estimate** and turn on **All fields**. Compare **Invoice Id** and **Invoice Date** in packets **01** and **02**, scrolling horizontally if needed. A blank cell means no value was returned; check the PDF to distinguish an unstated fact from missed extraction. Packet **03** has a multiple-document warning because this field grid shows only the first estimate; use **Classification** to inspect both.
4. Expand **Line Items** using its table icon. Compare packet **01**'s five rows with packet **08**'s three. The same fields repeat for each item; inspect their values and source boxes rather than treating the array as one value.
5. Switch to **ID**, **1099-A**, **Towing Invoice**, and **Rental Invoice** to compare their field coverage. Turn on **Confidence** to inspect returned scores. A blank score means the service omitted it, not zero; even high confidence does not prove a value is correct.

> [!Note] The included cached router has no `statement` route. Those pages remain **Other**, which the grid hides but retains in native JSON. Your step 4 router includes Statement.

> [!Note] **Checkpoint:** you can spot missing or repeated document types and fields across a collection. Populated fields alone do not establish extraction accuracy.

===
## Step 6: Investigate consistency checks

Plausible-looking fields can hide extraction errors. **Check consistency** applies fixed business rules to the returned values, highlighting relationships that need source review rather than proving extraction accuracy.

| Check | Business rule |
| :--- | :--- |
| **Total Amount, SubTotal, Tax verification** | SubTotal plus tax equals Total Amount. |
| **Repair line items, SubTotal verification** | Repair line-item amounts sum to the explicit SubTotal. |
| **Multiple Estimates Warning** | Compare quoted totals from repair estimates in the same packet. |

1. Select **Check consistency**. It uses the same loaded CU results; switching tabs does not submit analysis.
2. Open packet **03**'s **Warn** under **Multiple Estimates Warning**. Compare the two shops' **$1,699.04** and **$1,827.24** quotes with their source documents. Different quotes are legitimate business variation, not automatically an extraction error.
3. Open packet **08**'s red **Error** under **Repair line items, SubTotal verification**. The saved result shows `USD 980.00 + 124.00 + 0.00 = 1104.00; Subtotal = 1600.00`. Review the explanation, then select the formula or its fields to inspect the source boxes. This repair PDF was deliberately changed to separate parts and labor amounts; the saved extraction used parts amounts as row totals and missed labor.

> [!Note] **Error** flags a failed business rule; **Warn** can mean competing quotes or missing inputs. Check the explanation and source before attributing a finding to extraction. **Pass** confirms only the tested relationship, not every extracted value.

### Improve the repair extractor and compare results

1. In **CU Studio**, reopen the editable custom **Repair Estimate** extraction project from step 2, not the router or classifier. This rerun needs a single-document repair extractor. Keep **GPT-5.5**, the existing schema and descriptions, source/confidence settings, and `TotalAmount.Amount` extraction behavior.
2. In the `LineItems` item object, add these two **number / Extract** fields immediately **before** `TotalAmount`:

   | Field | Description |
   | :--- | :--- |
   | `PartsAmount` | `Part amount associated with each line item` |
   | `LaborAmount` | `Labor amount associated with each line item` |

   Keep the field order `PartsAmount`, `LaborAmount`, then `TotalAmount`. Do not replace `TotalAmount`; the consistency check continues to prefer a returned row total and uses parts plus labor only when that total is missing.
3. Upload and test [packet 08's repair estimate](../data/documents/packet-08/05-estimate.pdf) in Studio before building. Inspect every line item and its source regions. For this document, parts plus labor should produce:

   | Line item | PartsAmount | LaborAmount | TotalAmount |
   | :--- | ---: | ---: | ---: |
   | 0 | 980.00 | 223.20 | 1203.20 |
   | 1 | 124.00 | 62.00 | 186.00 |
   | 2 | 0.00 | 210.80 | 210.80 |

   The explicit `SubtotalAmount` is `1600.00`. Verify the actual Studio result; model runs are not guaranteed to return the same values.
4. Save and build with a new unique analyzer name. Wait for **Ready**, then copy the name exactly. Return to packet **08**'s error in the Workbench, enter it in **Updated repair estimate analyzer name**, and select **Rerun**. This submits only `05-estimate.pdf` as a fresh, billable CU call, with no second confirmation dialog.
5. Wait for the spinner to finish. The updated result appears below the original with its own status, calculation, and returned parts/labor fields. Select each result to compare its source boxes. A reconciled result should show `USD 1203.20 + 186.00 + 210.80 = 1600.00 (Subtotal)` and **Pass**. If it still fails, inspect the returned rows rather than assuming the new fields fixed it.

> [!Note] The rerun preview is browser-only; it does not change saved extraction results or native JSON. Another rerun replaces it, and refreshing the page or changing runs clears it. If the source cannot be matched to one individual PDF, correct the router's document boundaries in Studio before rerunning.

> [!Note] **Checkpoint:** you can use a failed business rule to focus source review, distinguish quote variation from extraction errors, and compare original and refined results.

> [+Note] **Where the files are**
>
> `instructions\lab.md` is the attendee guide. `infra\setup.ps1` installs dependencies; `infra\launch-workbench.ps1` launches only the app. `src\workbench` contains the app runtime, not another lab guide.
>
> `data\packets`: 10 complete customer PDFs. `data\documents\packet-01` through `packet-10`: 90 individual logical-document PDFs, extracted from the authored page groups. `data\samples`: six small Studio specimens. `data\packets.json`: source hashes and authored page ranges. `data\results`: run manifests and native CU JSON responses; future live runs save here too.
>
> `data\step1` through `data\step4` are convenience copies of the recommended inputs, not a second dataset. The app uses the canonical PDFs under `data`. Full packet 01 contains a statement and rental billing; full packet 03 contains towing. The step 3 classifier labels statements and both invoice types as Other; step 4 adds their named categories and routes. The included cached run predates the Statement route.

===

## Step 7. Check policy compliance using Azure Search (Foundry IQ) knowledge
### Explore cached policy reviews

**Check policies** uses an agent and retrieved policy evidence for five rental-processing checks. Neither changes the other's results. Selecting a policy check opens its finding and claim-versus-policy values in the right panel. Select a linked value to inspect its source PDF, then **Back to policy check** to return. The loaded CU results remain shared across tabs.

The repository includes ten saved agent reviews from the current packet dataset and Search-managed Standard index. These are portable: on another machine, start the app and select **Load cached results** without restoring `.tools` files, signing in to Azure, or deploying Search. The **Bundled demo** label identifies the saved reviews and their source index. Loading makes no Azure calls and does not enable follow-up chat. If you later change the extraction dataset, the app labels unmatched bundled reviews as **Stale policy results from a different extraction dataset** rather than presenting them as current results. Setup above connects the app to Azure for live reviews; it is not required just to view the saved bundle.

1. Open the **Check policies** tab. If you haven't loaded extraction results yet, first select **Parse and extract** > **Load cached results**, then return to **Check policies**.
2. Select **FoundryIQ**, then **Load cached results**. The included bundle loads all ten cases and 50 saved checks as read-only results; no Azure calls are made.
3. Select packet **02 / Washington**, then open its **Satisfied** **Daily cost** check. In the right panel, compare the claim's **$61/day** base rate and **five billed days** with the retrieved Washington rental terms: an **$85/day** contractual cap and a **30-day** limit. Notice that the agent identified the terms associated with this claim rather than applying a generic rental rule.
4. Open the **Source** links to inspect the underlying policy files and cited pages. Follow the Washington rental terms and SOP evidence, then select **Back to policy check** to return to the finding. The SOP's **$60** routine handling authority is separate from the **$85** contractual cap: a satisfied daily-cost check does not authorize payment. Inspect **Rental dates**, **Active policy**, **Covered charges**, and **Payment approval** to see where additional evidence or human review is needed. A check mark means **Satisfied**; an open circle means **Review required**. The circular-arrow **Waiting for info** status means missing claim evidence or approval, not a model still running. **N/A** identifies a check that doesn't apply.

| Case | CU daily base | Contractual daily cap | Retrieved SOP routine authority | Included saved daily-cost result |
| :--- | ---: | ---: | ---: | :--- |
| Packet 01 / Texas | $54 | $85 | $75, inclusive | **Satisfied**: $54/day and four billed days fit the contractual limits |
| Packet 02 / Washington | $61 | $85 | $60, inclusive | **Satisfied**: $61/day and five billed days fit the contractual limits; payment authority is separate |

In the refreshed saved reviews, both packets show **Waiting for info** for rental dates and insurer approval. Packet 02's **Covered charges** requires review because its local rental levy needs supporting evidence. These saved results are model-generated, not scripted outcomes.

5. [] For packet **01**, select the Texas **Source** link. Inspect **TX-R2** on page 2 and **Schedule A** on page 3 of `tx-rental-review-sop-v2.pdf`. The $75 value is internal routine handling authority, not the $85 contractual cap. Blank cells in the exception table don't grant extra authority. Also inspect the matching revised declarations, rental terms/diagram and issued amendment. The blank optional-code cell must not shift the Honda's deductible or rental limits.
6. [] In the source viewer, compare **Document**, **CU Search** and **Digital parse**. CU Search uses `prebuilt-documentSearch` and its own analyzer-keyed cache, not relabeled Layout output. Select **Back to policy check** to restore the finding. Optionally inspect Washington's scanned SOP or Arizona's image-based eligibility flowchart. A missing extraction has an explicit billable generation action; switching tabs alone doesn't call CU.
7. [] Optionally explore **Ask agent** in the right panel to ask additional questions about the selected claim. The bundled results are read-only, so this button is disabled for the cached demo. To use it, complete [Prepare live policy checks](#prepare-live-policy-checks), select **Run live**, and confirm the billable operation. Once a live-compatible review is available, select **Ask agent** and ask, "Why is Washington's daily cost satisfied, and what still needs human review? Cite the rental terms and distinguish routine authority from the contractual cap." Chat uses the selected case and mode without replacing its saved checks; each submitted question can incur Azure charges.

   During a live run, the status banner names the active packet and shows elapsed time. Each uncached packet gets one Search prefetch and five parallel Agent Framework calls, one per check. Missing claim fields can require one additional whole-packet CU extraction. Keep the tab open; refresh the same tab to resume progress rather than starting another run. Matching current reviews load from cache without another model call. **Run live** isn't a force-refresh button. You can also select **No policy retrieval** to inspect a saved baseline if available, then return to **FoundryIQ**; changing the dropdown alone doesn't submit a new run.

The agent connects fields extracted from the claim to the business rules and policy evidence associated with that claim. Its findings and linked sources help reviewers understand which checks are satisfied and where humans should spend time reviewing missing evidence, exceptions, or approvals. The agent supports that review; it does not make the final claim or payment decision.

These are source-based examples, not guaranteed model answers. Inspect differing results, missing facts or errors rather than forcing a pass. The SOP cannot supply a missing contractual benefit. Missing actual repair dates or pending insurer approval produce **Waiting for info**; contradictory evidence or unclear controlling rules require review. An issued amendment and its effective time, not a customer signature alone, establish changed terms. **Satisfied** for daily cost doesn't approve the claim or authorize payment.

### Optional: inspect Search, policy files and the agent

| Inspect | Where to look | What to learn |
| :--- | :--- | :--- |
| Active Search index | Note the index below **Policy retrieval**. In the [Azure portal](https://portal.azure.com/), open the Search resource matching `searchEndpoint` in `.tools\policy-agent-framework.json`, then **Indexes** > the active index > **Search explorer**. Search `rental daily rate`. | Chunks carry policy text, document identity, version and page information. The agent filters to the loss state and verified source generation. |
| Original policy files | Open the [v2 corpus](../data/policies/rental/ocr-comparison-v2/), especially the [Texas SOP](../data/policies/rental/ocr-comparison-v2/tx-rental-review-sop-v2.pdf) and [manifest](../data/policies/rental/ocr-comparison-v2/manifest.json). | CU must preserve table structure, blank cells, scanned text and figures so rules can be retrieved and cited. |
| Blob ingestion, if deployed | In Search, inspect the matching **Data source**, **Indexer** and **Skillset**. Follow the actual container to the storage account's **Storage browser**. | Managed ingestion reads policy PDFs from Blob Storage, runs the CU skill and indexes chunks. The Layout index alone doesn't prove this pipeline exists. |
| Agent Framework | Open [`infra/policy-framework-agent.py`](../infra/policy-framework-agent.py). Find `Agent`, `OpenAIChatClient` and `search_policy_rules`. | Initial reviews use five parallel calls with relevant CU fields and prefetched rules; follow-up chat can use the Search tool. |

For shared-resource names and subscriptions, see [under the hood](../docs/policy-checks.md#optional-look-under-the-hood). Don't change roles, networking or shared resources during this exercise.

**FoundryIQ** is the lab's umbrella label for grounded retrieval. This implementation queries an ordinary Azure AI Search index directly, not a Foundry IQ knowledge base. Setup builds a Search-managed **Standard** index with semantic chunks and AI figure descriptions. The bundled reviews record the Standard index used for their export; loading them does not query any currently configured index. Older local caches may retain **CU Layout** provenance. **CU Search** and **Digital parse** document tabs are separate cached representations; changing the viewer doesn't change the active Search index.

### Prepare live policy checks

The policy agent runs locally in Python Agent Framework and queries an ordinary Azure AI Search index. There is no hosted agent to create in Studio. Studio sign-in does not authenticate the local app.

Setup above has already indexed the policies, prepared the claim-summary analyzer and activated `.tools\policy-agent-framework.json`. No additional deployment command is needed here. The claim analyzer extracts facts from customer packets, not policies for Search, and is separate from the router you built in step 4. If you rerun deployment after launching the app, restart the app and reload the browser before continuing.

Load the CU results and open **Check policies**. Check the displayed setup status and index before selecting **FoundryIQ** > **Run live** and confirming the billable operation. A configured status reports local configuration, not a successful live connection. Saved results do not prove that Search or the model is reachable. Follow-up chat requires a live-compatible review, not the read-only bundled demo.

If live work fails, keep the exact error and use the [troubleshooting table](../docs/policy-setup.md#troubleshoot-live-policy-setup). Do not repeatedly submit billable runs to diagnose a configuration problem.

### 
---