@lab.Title

## Welcome to your lab environment

To begin, log into the virtual machine using the following credentials: +++@lab.VirtualMachine(Win11-Pro-Base).Password+++

**Note:** Select an insertable value to enter it without typing. Bold text identifies controls to select or results to inspect, not text to enter.

# From documents to an insurance workbench

This lab builds on document extraction concepts from Azure AI Document Intelligence and uses Azure Content Understanding (CU) to turn synthetic insurance documents into structured, source-linked results. You'll build and test analyzers in Content Understanding Studio (CU Studio), then connect your finished analyzer to a **separate Insurance Workbench application**.

Imagine you're reviewing an insurance claim. Open the supplied [customer packet](../data/step3/packet-01.pdf) and browse its 13 pages: a membership card, policy, claim form, incident report, repair estimate, handwritten statement, rental invoice, inspection, and tax form. Your goal is to identify each logical document, extract the details needed for claim review, and trace those details back to their source pages. A two-page invoice must stay together, and a proposed repair amount must remain distinct from an invoiced charge or proof of payment.

An **analyzer** is a reusable configuration that tells CU how to process content. An extraction analyzer defines which fields to return and how to extract or generate them. A classification analyzer identifies document categories and boundaries; adding extraction routes sends each category to its corresponding analyzer. A Studio project is where you edit and test that configuration before building an analyzer for the app to use.

Along the way, you'll:

- **Explore prebuilt analyzers:** compare document layout with pre-built extraction models, and inspect how returned values relate to the source documents.
- **Customize extraction:** extend an invoice template to extract vehicle, VIN, and odometer details from a repair estimate, then build a Statement analyzer that combines extracted facts with grounded summaries.
- **Classify and split document packets:** identify document types and logical page ranges in mixed insurance packets, keeping continuation pages together without extracting fields yet.
- **Add extraction routes:** connect document categories to prebuilt analyzers and your custom repair and Statement analyzers, including dedicated routes for towing and rental invoices. Review the returned fields and source highlights.
- **Review results in the Insurance Workbench:** explore saved results, investigate consistency checks, compare policy reviews with and without retrieval, then connect your own built analyzer to run live analysis across ten customer packets.

===

## Step 1: Explore prebuilt analyzers

To get started, explore the prebuilt analyzers in CU Studio by uploading and analyzing a few sample documents.
This will help you understand the distinction between layout extraction and schema-based extraction before you move on to customizing your own analyzers.

Open the browser and navigate to the CU Studio gallery: +++https://contentunderstanding.ai.azure.com/discover+++.
Click **Sign in** on the top right corner of the page and log in with the provided credentials for Azure:
- Username: +++@lab.CloudPortalCredential(User1).Username+++
- If prompted for a Temporary Access Pass (TAP): +++@lab.CloudPortalCredential(User1).AccessToken+++
- If prompted for a Password: +++@lab.CloudPortalCredential(User1).Password+++

Once done, follow the steps below to explore the prebuilt analyzers:
1. Click on **Layout** to test the document layout extraction. When prompted to confirm the details of the subscription, resource group and resource name, confirm default selections and proceed. Click **Next**->**Save**.
2. You'll get a list of samples for different content types (checklist, financial report, formulas, etc). Select a sample to see the original document scan and how the prebuilt analyzer extracts information from it.
!IMAGE[chshn4cn.png](instructions359897/chshn4cn.png)
3. Select **Browse for files** to upload your own document for analysis. In the File Explorer window that opens, navigate to +++C:\Users\LabUser\Desktop\ignite26-LAB664\data\step1+++ and select **towing-invoice.pdf**. Notice how both the content and the format (tables, lists, headers) are extracted and displayed on the right side panel.
!IMAGE[xfe4ei8u.png](instructions359897/xfe4ei8u.png)

Next, compare layout extraction with schema-based extraction for the same document.
1. Select the **Back** arrow in the upper-left corner of the Studio page to return to the gallery.
2. In the gallery, scroll down to **Procurement**, then select **Invoice**.
3. Inspect the default sample to see how schema-based extraction identifies specific fields, such as **AmountDue**, **BalanceForward**, and **Billing Address**, with corresponding confidence scores.
4. Upload the same **towing-invoice.pdf** document. Compare its extracted fields and confidence scores with the layout results from the previous exercise.

Feel free to experiment with further pre-built analyzers to understand how CU Studio handles different document types and extraction scenarios. Below you can find a few examples of prebuilt analyzers along with the sample documents provided in the data folder, and the fields they extract.

| Prebuilt in Studio | Upload | Inspect |
|:---|:---|:---|
| Identity / Generic ID document | demo-id.pdf | Named holder and available ID-like fields. This fictional membership specimen is not a government ID. |
| US tax / 1099A | form-1099a.pdf | Tax year, lender, borrower, account, and form boxes. Nested year/copy results are not extra input documents. |

> [!Note] **Checkpoint:** you can explain the difference between document layout and schema-based extraction.

===

## Step 2: Build a custom repair extractor

In the following step, we will build a custom repair extractor to handle repair estimate documents specifically. This involves creating a new extraction project, defining the necessary fields, and testing the extraction on a sample repair estimate PDF.

For this step, use the **gpt-5.5** model instance pre-provisioned and mapped by the lab template. 

1. Move from the **Discover** to the **Build** tab, by selecting it on the top right corner of the blue top navigation bar.
2. Click on **Create** to start building your custom repair extractor.
3. Enter +++custom-repair-extractor+++ as the project name.
4. Select **2026-06-01 (Preview)** as the API version and **Standard Extraction** as the workflow type.
!IMAGE[kke6gm3z.png](instructions359897/kke6gm3z.png)
5. Expand the **Advanced settings** section and select **gpt-5.5** as the model.
6. Leave the other parameters at their defaults and select **Create**.
!IMAGE[qm5a1m18.png](instructions359897/qm5a1m18.png)
7. Once your project is created, select **Browse for Files** and upload +++C:\Users\LabUser\Desktop\ignite26-LAB664\data\step2\repair-estimate.pdf+++. Select **Run analysis**.
8. In the **Choose a template window**, select the **Invoice** one. Click on **Save** to proceed.
9. Add **these three lowercase fields**, with method **Extract**, one by one. For each field, enter the field's **Name** and **Description** from the table below. Complete both cells before selecting **Add field** again, and repeat for all three rows.

| Field | Type / method | Copy this description |
|:---|:---|:---|
| +++vehicle+++ | String / Extract | +++Printed vehicle name as one string, including year/make/model when present. Do not add color, decode the VIN, or infer missing details.+++ |
| +++vin+++ | String / Extract | +++Exact value explicitly labeled VIN. Do not correct it or substitute registration, plate, or account numbers. Leave unset if absent.+++ |
| +++odometer+++ | Number / Extract | +++Printed Odometer or Inspection Mileage as a number. Remove grouping separators; no units. Do not substitute Annual Mileage or infer an absent value.+++ |
10. Click on **Save** to confirm the added fields.
!IMAGE[y1l65rn4.png](instructions359897/y1l65rn4.png)
11. **Run analysis**.
!IMAGE[ctdjrztc.png](instructions359897/ctdjrztc.png)
12. Inspect the returned values rather than entering them: **vehicle** should be **2019 Toyota Corolla LE**, **vin** should be **5YFEPMAE3KA513905**, and **odometer** should be **94360**. The repair proposal total is **$1,310.13**.
13. After reviewing the results, select **Build analyzer**. Enter +++repair_extractor_analyzer+++ as the name and +++Extractor for repair estimates based on uploaded documents+++ as the description. Select **Build**.
!IMAGE[eli9ysmu.png](instructions359897/eli9ysmu.png)
14. Once you are prompted with 'Built successfully', your analyzer is ready for use. Click on **Jump to analyzer list** to verify the analyzer details. You'll find your newly created analyzer in the **Analyzer list**.
!IMAGE[22c2gk9p.png](instructions359897/22c2gk9p.png)

### Add a custom statement extractor

Now let's work with a different kind of document: a claimant's account of an incident. Unlike an invoice, a statement may describe the same damage in several places or leave important details unstated. You will use **Extract** for facts explicitly present in the document and **Generate** for a concise, grounded synthesis of the narrative.

Instead of entering each field manually, you will import a prepared schema and inspect how its field descriptions constrain the result.

1. Return to **Build** > **Project list** and create a second **Standard Extraction** project using the **2026-06-01 (Preview)** API version. Enter +++custom-statement-extractor+++ as its name.
2. In **Advanced settings**, select **gpt-5.5**, then select **Create**.
3. Select **Browse for Files**. In the File Explorer window, navigate to +++C:\Users\LabUser\Desktop\ignite26-LAB664\data\documents\packet-01+++ and select **06-handwriting.pdf**.
4. In the pop-up that appears after the document upload, keep **Document Analysis** as selected template, disable **AI-Powered field suggestions**, then select **Save**.
!IMAGE[szpjguew.png](instructions359897/szpjguew.png)
5. In the field-schema toolbar, choose **Import**, navigate to +++C:\Users\LabUser\Desktop\ignite26-LAB664\data\step2+++, and select **statement-schema.json**. Confirm schema replacement if prompted, then select **Save**. This imports the fields and descriptions; no field-by-field typing is needed.
!IMAGE[03cudcq2.png](instructions359897/03cudcq2.png)

Inspect the imported schema: **seven flat fields, five Extract and two Generate**, with **Source & Confidence** enabled. These fields are already imported; don't add them again. Read the descriptions for **incident_date**, **reported_damage**, and **summary** to see how they distinguish stated facts from grounded synthesis without inferring fault, coverage, or payment.

6. Wait until saving indicators clear, then select **Run analysis** to test the uploaded handwritten statement. Inspect the returned facts alongside the source document.
   - Check that **claimant_name** is **Danielle Ortiz** and **incident_date** is **2026-02-12**. The incident date is February 12, not the February 13 date at the top of the letter. These are expected results, not values to enter.
   - The five *Extract* fields contain stated facts; the two *Generate* fields provide readable, grounded synthesis rather than verbatim quotes.
   - Inspect source highlights and confidence where returned. 
   - If a fact is not stated in the document, check that the analyzer leaves the corresponding field empty rather than guessing a value.

> [!Tip] 
> Leave **Hide missing fields** off to see fields that aren't populated. If you previously turned it on, turn it off.
>
> !IMAGE[33b9kcoj.png](instructions359897/33b9kcoj.png)

Next, test the same schema against a typed email:

1. Select **Browse for Files** and upload +++C:\Users\LabUser\Desktop\ignite26-LAB664\data\samples\email-statement.pdf+++. Save the project, wait for saving to finish, then select **Run analysis**.
2. Perform the same checks as in the handwritten statement. The incident date remains **2026-02-12**, not the email's February 13 sent date.
3. After reviewing both documents, select **Build analyzer**. Enter a new unique ID, for example +++statement_extractor_analyzer+++, and the description +++Custom analyzer for extracting facts from handwritten and typed statements.+++ In the **Analyzer list**, you should now see two custom analyzers, as in the screenshot below.
!IMAGE[516v1pe7.png](instructions359897/516v1pe7.png)

> [!Note] **Checkpoint:** your custom repair and statement analyzers have both been tested and built, and you have recorded both analyzer IDs.

===

## Step 3: Classify and split a packet, without extraction

So far, you've analyzed one document at a time. Return to the customer packet from the introduction: the app needs repair, statement, and invoice details from the same PDF, not just its raw text. First, create a classifier that identifies document types and splits the packet into logical documents. In step 4, you'll route those documents to extraction analyzers.

You will start with a small three-page packet, then test the same configuration against two larger packets. This will help you see the difference between a page boundary and a document boundary.

### Create the classification project

1. Return to **Build** > **Project list** in CU Studio. Select **Create**, choose **2026-06-01 (Preview)** before selecting **Classification**, and enter +++packet_classifier+++ as the project name.
!IMAGE[9maoqxjx.png](instructions359897/9maoqxjx.png)
2. In **Advanced settings**, select **gpt-5.5** as **Model for Analysis** and create the project.
3. In the new project, select **Browse for files**. Navigate to +++C:\Users\LabUser\Desktop\ignite26-LAB664\data\step3+++ and select **classification-packet.pdf**.
 
> [!Note] **Upload first:** the routing-rule editor becomes available after a file is uploaded.

4. In **Routing rules**, add the four category keys and descriptions in the table below, one by one. For each category, enter the category's **Name** and **Description** from the table. Keep the keys exactly as shown. Complete both cells before selecting **Add category** again, and repeat for all four rows.
!IMAGE[7qhnpb5o.png](instructions359897/7qhnpb5o.png)

> [!Note] **Do not assign child analyzer IDs yet**; you will add extraction routes in step 4.

| Category key | Copy this description |
|:---|:---|
| +++id_document+++ | +++The lab's identity-like demo card with named holder, portrait and membership identifier. This synthetic membership card demonstrates ID field extraction, not government-ID authenticity. Exclude invoice, tax and repair documents.+++ |
| +++tax_1099a+++ | +++An IRS Form 1099-A Acquisition or Abandonment of Secured Property, including fictional borrower-copy examples. Exclude other tax forms and prose references.+++ |
| +++repair_estimate+++ | +++A standalone repair workshop estimate or quote with vehicle details and proposed parts/labor. Keep continuation pages of the same estimate together; split a different estimate even if adjacent. Exclude towing/rental/glass invoices and their supporting inspection supplements even when they mention a proposed repair schedule.+++ |
| +++other+++ | +++Each distinct supporting document: policy declarations/endorsements, claim intake forms, incident reports, handwritten statements, towing/rental/glass invoices with their own continuation supplements, valuation/downtime schedules, and workshop inspection records. Identify logical boundaries even when adjacent documents both have category other. Keep paginated continuation pages together; do not merge different document titles or identifiers. These documents are unrouted, not discarded.+++ |

Next, configure how the classifier separates documents:

1. In **Routing rules**, turn on **Enable segment**, then open the settings panel, by clicking on the gear icon. Select **Auto segment content**, leave **Allow in-page segments** off, and do not select **Segment by page**. Close the dialog and leave other settings unchanged.
!IMAGE[9zacnykv.png](instructions359897/9zacnykv.png)

> [!Note] With the configured settings, a two-page rental invoice should remain one logical document. Two adjacent documents should still be separate, even when both belong to `other`.

2. Select **Save** and wait until saving indicators clear before changing tabs. Select **Run analysis** and remain in the project until it finishes. Inspect the results to ensure documents are segmented correctly.
3. In **Test**, inspect the **classification and page count** shown for each segment. The **Segment** selector initially shows the retained parent, **input1**. Open it and select each child segment to see its category and page range. Expect **id_document** on page 1, **tax_1099a** on page 2, and **repair_estimate** on page 3: one page each. Every page should be covered once. Classification-only child segments have **Result**, not domain extractor fields.
!IMAGE[s51l89mw.png](instructions359897/s51l89mw.png)
4. To keep a before/after comparison, select the parent `input1`, then **Result** and **Download** to save the JSON. 
!IMAGE[n0m86b6w.png](instructions359897/n0m86b6w.png)

> [!Tip] Download results before leaving the project or adding routes; reopening a saved project does not restore the displayed analysis results.

### Test the full customer packet

In the previous step, you tested a small packet to ensure the classifier correctly segments individual documents. Now, you will test the full customer packet to verify the classifier's behavior on larger, multi-document files.

1. Within the same project, select **Browse for Files** and upload +++C:\Users\LabUser\Desktop\ignite26-LAB664\data\step3\packet-01.pdf+++.
2. Select **Run analysis**. After it finishes, inspect each segment's classification, page count, and page range. Compare the returned boundaries with the individual PDFs under `C:\Users\LabUser\Desktop\ignite26-LAB664\data\documents\packet-01`. Use the authored document groups below as a reference:

| Pages | Logical document | Category at this stage |
|:---|:---|:---|
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

> [!Tip] Below each segment name, inspect its classification and page count. For example, the rental invoice should span **two pages, 10-11**, as one logical document.
> !IMAGE[vcl16bde.png](instructions359897/vcl16bde.png)

4. Next, upload **packet-03.pdf** from the same folder and run analysis. Review its 13 pages against the individual files in `C:\Users\LabUser\Desktop\ignite26-LAB664\data\documents\packet-03`, then download the parent result. Use the same boundary checks as for packet 01, but don't reuse its page ranges: the two separate repair estimates are on **pages 8 and 9**, the statement is on **page 10**, and the towing invoice is on **page 11**.
5. Before moving to the next step, select **Build analyzer** and enter a unique ID such as +++packet_classifier+++. Enter +++Classifier for multi-document analysis+++ as the description.
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
|:---|:---|:---|
| `id_document` | `prebuilt-idDocument.generic` | Keep the step 3 description. |
| `tax_1099a` | `prebuilt-tax.us.1099A` | Keep the step 3 description. |
| `repair_estimate` | Your `repair_extractor_analyzer` ID | Keep the step 3 description. |
| `other` | **No route** | +++Each distinct unrouted supporting document: policy declarations/endorsements, claim intake forms, incident reports, glass/panel service supporting records, valuation/downtime schedules, and workshop inspection records. Statements, towing bills, and rental billing belong to their named categories, not Other. Identify logical boundaries even when adjacent documents both have category other. Keep continuation pages together; do not merge different titles or identifiers. These documents are unrouted, not discarded. Exclude towing/recovery/security charge supplements; classify those as towing_invoice.+++ |

3. Select **Add category** and enter `statement` with its description below, then select your custom Statement analyzer through **Analyzer ID** > **Custom**. Repeat for `towing_invoice` and `rental_invoice`, selecting `prebuilt-invoice` through **Prebuilt** for each. Complete each name and description before adding the next row.
!IMAGE[ujvd6zg6.png](instructions359897/ujvd6zg6.png)

| Category key | Extraction route | Description change |
|:---|:---|:---|
| +++statement+++ | Your `statement_extractor_analyzer` ID | +++A handwritten or typed claimant statement or email describing the incident, claimant vehicle, and reported damage. Keep continuation pages of the same statement together. Exclude claim forms, incident reports, witness or other-driver accounts, and repair or invoice documents.+++ |
| +++towing_invoice+++ | `prebuilt-invoice` | +++A towing or roadside-recovery invoice, bill or charge ledger for vehicle transport, storage or release. Keep continuation and release/custody supplements from the same bill together. Payment may be unpaid or pending; do not infer payment. Exclude repair estimates, rental billing, and glass or panel service quotes. Include towing/recovery/security charge supplements that list service charges or a total due, even when they also contain inspection details or repair-quote references.+++ |
| +++rental_invoice+++ | `prebuilt-invoice` | +++A vehicle rental billing document or invoice with rental agreement references, dates or daily charges. Keep the same agreement's pickup/billing/vehicle-condition continuation pages together. Payment may be unpaid or pending; do not infer payment. Exclude towing bills, repair estimates, and glass or panel service quotes.+++ |

4. Verify there are **seven categories and six assigned routes**, with no route for `other`. Keep **Enable segment** on and retain the segmentation settings from step 3; there's no need to reopen the settings panel if you haven't changed them.
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
   - Select **packet-03.pdf** and run analysis. Inspect the two repair estimates on **pages 8 and 9**, the Statement route on **page 10**, and the towing invoice on **page 11**, along with the other categories and logical boundaries. Check invoice amounts against the towing supplement's **$237 charge**, not the separate **$1,699.04 repair quote** it references. Download the parent result. Other documents remain in the parent content without a domain extraction route.
10. Compare returned fields with their source documents. Keep claimant-reported details distinct from verified facts, and proposed repair amounts distinct from invoiced charges or proof of payment. If a fact isn't stated, check that its field is unset rather than invented. Leave **Hide missing fields** off to see fields marked **Not found**; change it only if you previously turned it on.
11. After reviewing all three packets, select **Build analyzer** and enter a new unique ID, such as +++router_analyzer+++. Do not overwrite the classification-only analyzer you created in the previous step. After a successful build, use **Jump to analyzer list**. Verify this exact analyzer has status **Ready**. Record its ID and your resource endpoint for step 5.

> [!Note] **Checkpoint:** a tested, ready router links every non-Other category to extraction.

===

## Step 5: Connect to your separate Insurance Workbench app

In the final step, you will move from authoring analyzers to reviewing their results in an application. The Insurance Workbench loads ten customer packets, totaling 118 pages, from `data\packets`; you do not need to upload them manually.

You will first explore the included saved results without submitting analysis. Then you will investigate consistency checks and compare policy review with and without retrieval. Finally, you can connect the router you built in step 4 and explicitly start a live run. CU Studio remains your tool for editing and building analyzers.

### Prepare and launch the app

The app requires **Python 3.10 or later**, including pip and venv. Use the prepared lab environment, where everything has been pre-installed for you.

1. Open **Windows PowerShell** CLI and move to the repository root, the folder containing `src`, `data`, and `infra`:

   ```PowerShell
   Set-Location "C:\Users\LabUser\Desktop\ignite26-LAB664"
   ```

2. Run the setup command below. It restores the app's locked npm dependencies, including Deep Chat, and prepares the Python Agent Framework environment in `.tools\policy-venv`. It also installs a supported Node runtime or Azure CLI if missing.

   ```PowerShell
   powershell -ExecutionPolicy Bypass -File .\infra\setup.ps1
   ```

3. After setup completes, restore the included synthetic policy reviews and claim fields:

   ```PowerShell
   powershell -ExecutionPolicy Bypass -File .\infra\policy-demo-cache.ps1
   ```

   This command makes no Azure calls, contains no credentials, and refuses to replace different local configuration or cache files. If it reports a conflict, ask the lab owner to review it rather than deleting your local files.

3. Login to Azure via the az CLI:

   ```PowerShell
   az login
   ```
   
   This command opens a browser window for you to sign in with the Azure account you used to log into the CU studio. Select **Work or School account** and complete the sign-in process with the credentials provided in the **Resources** tab. When asked, confirm the Azure subscription shown in the CLI with enter.

4. Launch the separate app and keep this terminal open:

   ```PowerShell
   powershell -ExecutionPolicy Bypass -File .\infra\launch-workbench.ps1
   ```

5. Open +++http://127.0.0.1:8791/+++ in a new browser tab. Do not open `workbench.html` directly.

> [!Note] To stop the app at anytime just return to PowerShell and press **Ctrl+C**. 

### Explore the included results first - no Azure analysis on load

1. In **Parse and extract**, select **Load cached results** to load the included completed **10/10** run. The Cached badge identifies historical native CU JSON, not a fresh run or your new analyzer. Its tooltip preserves the original analyzer, API version, timestamp, and dataset fingerprint. Results and fixed extraction checks load before the table appears; saved rental-policy reviews are loaded separately in **Check policies**. Loading either cache makes no paid model calls.
2. Start with **Classification**. Each row is one customer; each check is a returned document instance and page range. Click a check or field value to open its full source PDF at that page. Other is hidden from this grid, not removed from the response.
3. Switch to **ID**, **1099-A**, **Repair Estimate**, **Statement**, **Towing Invoice**, and **Rental Invoice**. Only returned types appear. Repair defaults show vendor, vehicle, VIN, total, tax, and line items; use **All fields** for odometer. Statement shows returned fields from its seven-field schema with native source and confidence; unstated values are not invented, and globally empty columns are hidden.
4. Turn on **Confidence** to inspect returned scores. Blank means the service omitted a score, not zero. Click line items for source boxes or their table icon to expand item rows below the customer. Click a subfield to highlight its source while keeping the rows open. Drag column edges or the PDF divider to resize. Double-click a field to focus at 300%; double-click again to fit. Use wheel zoom, drag-to-pan, and the bottom page controls.
5. Use **{ }** to download the complete native JSON for the selected customer. Compare it with the source PDF; values, geometry, and confidence come from CU, not fabricated app output.

### Compare policy review with and without retrieval

Use the top-level tabs to move between **Parse and extract**, **Check consistency**, and **Check policies**. **Check consistency** validates returned fields, arithmetic, and cross-document consistency. **Check policies** uses an agent and retrieved policy evidence for five rental-processing checks. Neither changes the other's results. Selecting a policy check opens its finding and claim-versus-policy values in the right panel. Select a linked value to inspect its source PDF, then **Back to policy check** to return. The loaded CU results remain shared across tabs.

Load the current CU results first. In **Check policies**, the checked-in bundled reviews can be loaded as a read-only historical demo even though they were created from the original packet dataset. The app labels them **Stale policy results from a different extraction dataset** and does not present them as a fresh review of the customized packets. Loading them makes no Azure calls, does not replace the current Parse and extract results, and does not enable follow-up chat. The lab owner must complete [policy setup](../docs/policy-setup.md) before live policy work. Sign in with `az login` using your approved lab identity only when running live work.

1. Start with **Parse and extract** > **Load cached results**, then open **Check policies**, select **FoundryIQ**, and select **Load cached results**. The status identifies the historical bundled results as stale and read-only; no Azure calls are made.
2. To request live policy work, select **Run live** and confirm the operation for all loaded cases. The status banner names the active packet and shows elapsed time. Each uncached packet gets one Search prefetch and five parallel Agent Framework calls, one per check. Missing claim fields can require one additional whole-packet CU extraction. Azure charges apply.

   Keep the tab open; refresh the same tab to resume progress rather than starting another run. Matching current reviews load from cache without another model call. **Run live** isn't a force-refresh button.
3. Optionally select **No policy retrieval** to inspect a saved baseline if available, then return to **FoundryIQ**. Changing the dropdown alone doesn't submit a new run.
4. Inspect **Daily cost**, **Rental dates**, and **Active policy**, followed by **Covered charges** and **Payment approval**. A check mark means **Satisfied**; an open circle means **Review required**. The circular-arrow **Waiting for info** status means missing claim evidence or approval, not a model still running. **N/A** identifies a check that doesn't apply.

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

1. Reopen or reload [Insurance Workbench App](http://127.0.0.1:8791/). In **Analyzer**, select the exact ID you built in step 4, for example **router_analyzer**. The list contains ready custom logical classifiers/routers, not standalone prebuilts. If missing, check the endpoint, permissions, API version, and that the analyzer was built successfully.
2. Click **Run live**. Read the confirmation for ten packets / 118 pages; only confirm when you intend to incur Azure charges. The app submits each packet once to the selected ready router and uses its linked extraction routes. It does not create analyzers, deploy models, or add a separate Statement pass.
3. Watch progress and elapsed time. Each native response is saved under `data\results\RUN-ID` before results are derived. The live batch then runs the fixed extraction checks. Packet analysis incurs Azure charges. Completed results become a new cache entry. A failed run remains visibly failed; inspect its error before explicitly starting another billable run.
4. Compare your live extraction with the PDFs and the saved run. To see classification alone, select your step 3 analyzer, for example **packet_classifier**, and explicitly start a separate billable run. Fields appear only when extraction routes actually returned them.

> [!Note] **Checkpoint:** you connected CU results to a separate application, compared policy checks with and without retrieval, and traced a daily-rate result to its SOP.

### Investigate consistency checks and agent reviews

**Check consistency** uses fixed extraction and arithmetic rules to validate extraction accuracy. In this exercise, use the fixed repair error to identify issue with analyzer, improve it in CU Studio and compare results.

1. Select **Check consistency**. The matrix contains exactly three fixed extraction checks:
   - **Total Amount, SubTotal, Tax verification** asks whether SubTotal plus tax equals Total Amount.
   - **Repair line items, SubTotal verification** asks whether repair line-item amounts sum to the explicit SubTotal.
   - **Multiple Estimates Warning** warns when repair-estimate totals differ. It shows each shop and quote amount with a source link. This is a review warning, not proof of an extraction error.
2. Select the red **Error** for packet 8, **Repair line items, SubTotal verification**. The original Repair Estimate result shows the calculation `USD 980.00 + 124.00 + 0.00 = 1104.00; Subtotal = 1600.00`. Review the explanation and the formula fields, then select the source or formula to highlight the native values in the PDF.
3. In **CU Studio**, reopen the editable custom **Repair Estimate** extraction project from step 2. Do not edit the packet router or classification project: this rerun requires a ready single-document repair extractor. Keep the project on **GPT-5.5** and keep the existing schema, descriptions, source/confidence settings, and `TotalAmount.Amount` extraction behavior.
4. In the `LineItems` item object, add these two **number / Extract** fields immediately **before** `TotalAmount`:

   | Field | Description |
   |---|---|
   | +++PartsAmount+++ | +++Part amount associated with each line item+++ |
   | +++LaborAmount+++ | +++Labor amount associated with each line item+++ |

   Keep the field order `PartsAmount`, `LaborAmount`, then `TotalAmount`. Do not replace `TotalAmount`; the consistency check continues to prefer a returned row total and uses parts plus labor only when that total is missing.
5. In Studio, upload and test [packet 8's repair estimate](../data/documents/packet-08/05-estimate.pdf) before building. Inspect every line item and its source regions. A useful result for this document is:

   | Line item | PartsAmount | LaborAmount | TotalAmount |
   |---|---:|---:|---:|
   | 0 | 980.00 | 223.20 | 1203.20 |
   | 1 | 124.00 | 62.00 | 186.00 |
   | 2 | 0.00 | 210.80 | 210.80 |

   The explicit `SubtotalAmount` is `1600.00`. These values reconcile, but always verify the native Studio result rather than assuming a model run is deterministic.
6. Save and build the updated project with a new unique analyzer name. Wait until the analyzer is **Ready**, then copy its analyzer name exactly. Return to the packet-8 error in the Workbench, enter it in **Updated repair estimate analyzer name**, and select **Rerun**. This submits only `05-estimate.pdf` as a fresh, billable CU call; there is no second confirmation dialog.
7. While the spinner is active, wait for the rerun to finish. The updated result appears below the original with its own status and calculation. Its field table shows formula inputs plus returned `PartsAmount` and `LaborAmount`, grouped by numeric line-item index in the order total, parts, labor, followed by SubTotal. Select the original and updated results to compare their own source boxes. A successful updated result should show `USD 1203.20 + 186.00 + 210.80 = 1600.00 (Subtotal)` and change the check to **Pass**.
8. The rerun preview is temporary and browser-only. It is not written to the saved extraction cache or native JSON. Navigating within the current run keeps the original and latest updated result; another rerun replaces the previous preview. Refreshing the page or changing runs clears it. If the source cannot be matched to one individual PDF, return to Studio and correct the router's document boundaries before rerunning.

> [+Note] **Where the files are**
>
> `instructions\lab.md` is the Markdown version of this single guide; `instructions\lab.html` is the original HTML version. `infra\setup.ps1` installs dependencies; `infra\launch-workbench.ps1` launches only the app. `src\workbench` contains the minimal app runtime, not another lab guide.
>
> `data\packets`: 10 complete customer PDFs. `data\documents\packet-01` through `packet-10`: 90 individual logical-document PDFs, extracted from the authored page groups. `data\samples`: six small Studio specimens. `data\packets.json`: source hashes and authored page ranges. `data\results`: one included completed run with its original manifest and ten native JSON responses; future live runs save here too.
>
> `data\step1` through `data\step4` are convenience copies of the recommended inputs, not a second dataset. The app uses the canonical PDFs under `data`. Full packet 01 contains a statement and rental billing; full packet 03 contains towing. The authored four-class reference labels statements and both invoice types as Other, while the seven-class routed run gives them separate categories.

---