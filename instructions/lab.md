@lab.Title

To begin, log into the virtual machine using the following credentials: +++@lab.VirtualMachine(Win11-Pro-Base).Password+++

**Note:** Text formatted as an +++example+++ represents type text. Clicking on this text will automatically insert it to prevent any typing errors.

### From files to decisions

Turn insurance claim packets into source-linked facts with Content Understanding, then review and improve the results in the **Insurance Workbench app**.

- **Part 1 - Understand the documents:** classify and split packets, then extract required fields (steps 1-6).
- **Part 2 - Validate the data with business rules:** inspect results and identify a business-rule failure (steps 7-8).
- **Part 3 - Fix issues:** improve the repair analyzer and verify the highlighted failure again (step 8).
- **Optional - Apply policies:** use a Foundry IQ (Azure Search Index) retrieval and Agent Framework to compare claims with policy evidence (step 9).
- **Optional - Manage analyzers with a coding agent:** use GitHub Copilot and the Azure Developer CLI (`azd ai cu`) to manage and improve Content Understanding analyzers (step 10).
  
===

## Step 1: Environment setup

> [!Note] The following setup prepares the environment for the remaining steps of the lab. As it takes a few minutes, starting it now enables it to run while you explore analyzers in CU Studio. Keep the PowerShell window open and continue with the browser instructions below while it runs.

1. Open **Windows PowerShell**, pinned on the taskbar, and move to the repository root:

!IMAGE[dafb0t2p.png](instructions359897/dafb0t2p.png)

   ```PowerShell
   Set-Location "C:\Users\LabUser\Desktop\ignite26-LAB664"
   ```

2. Sign in with the Azure account provided below.

   ```PowerShell
   az login
   ```
   Choose **Work or School account** if prompted, then use the following credentials:

  - Username: +++@lab.CloudPortalCredential(User1).Username+++
  - If prompted for a Temporary Access Pass (TAP): +++@lab.CloudPortalCredential(User1).AccessToken+++
  - If prompted for a Password: +++@lab.CloudPortalCredential(User1).Password+++

Then select 'No, this app only' when asked to sign in to all apps and websites. 

!IMAGE[38jmsmpt.png](instructions359897/38jmsmpt.png)

Finally, confirm the subscription selection by pressing **Enter**.

!IMAGE[jueqmgw8.png](instructions359897/jueqmgw8.png)

3. Run the command below 

```PowerShell
powershell -ExecutionPolicy Bypass -Command "& '.\infra\setup.ps1'; & '.\infra\deploy.ps1' -ResourceGroup 'ResourceGroup1' -Apply"
```

   - **Setup.ps1** restores install a handful of dependencies for the Insurance Workbench used later in the lab. 
   - **Deploy.ps1** setup Azure Search (FoundryIQ) index to enable policy checks later in the lab.

> [!Note] Let the script run in the background. You will return to it in step 7 to check that setup completed and launch the app.
> Don't need to wait for it to finish. Leave this terminal open and proceed to step 2. 

===

## Step 2: Explore prebuilt analyzers

### Part 1: Understand the documents

### Explore the prebuilt analyzers in CU Studio

To get started, let's explore the prebuilt analyzers in CU (Content Understanding) Studio by uploading and analyzing a few sample documents.
This will help you understand the distinction between layout extraction and schema-based extraction before you move on to customizing your own analyzers.

Open the browser to navigate to the CU Studio Gallery (`https://contentunderstanding.ai.azure.com/discover`).
Click **Sign in** on the top right corner of the page and log in with the provided credentials for Azure:
- Username: +++@lab.CloudPortalCredential(User1).Username+++
- If prompted for a Temporary Access Pass (TAP): +++@lab.CloudPortalCredential(User1).AccessToken+++
- If prompted for a Password: +++@lab.CloudPortalCredential(User1).Password+++

### Try out Layout Analyzer

Once done, follow the steps below to explore the prebuilt analyzers:
1. Click on **Layout** to test the document layout extraction. 
2.  Click **Next**->**Save** to confirm details of subscription, resource group etc.
3. You'll get a list of samples for different content types (checklist, financial report, formulas, etc). Select a sample to see the original document scan and how the prebuilt analyzer extracts information from it.

!IMAGE[chshn4cn.png](instructions359897/chshn4cn.png)

4. Next, click on **Browse for files** to upload your own document for analysis. In the File Explorer window that opens, navigate to `C:\Users\LabUser\Desktop\ignite26-LAB664\data\samples` and select **towing-invoice.pdf**.
5. Explore the output in the right panel by navigating across the different tabs (**Markdown**, **Tables**, **Result**). It includes Markdown, document structure (tables, lists, headings), and JSON parsed from the document.

> [!Note] The Layout analyzer parses a file into standard Markdown and JSON representations. It uses OCR to extract text and also extracts additional structures like tables, headings, lists, formulas, and figures.

!IMAGE[xfe4ei8u.png](instructions359897/xfe4ei8u.png)

> [!Tip] If some tabs are hidden, click on the three-dot menu to reveal additional tabs.

### Try out Invoice prebuilt

Return to the previous page by clicking the **Back** button at the top left of the page.

!IMAGE[utcl2ivw.png](instructions359897/utcl2ivw.png)

Let's examine the differences between the prebuilt layout extraction and the schema-based extraction for the same document. 
1. Scroll down on the **Procurement** section to locate the **Invoice** prebuilt analyzer and click on it to open the details.
2. Inspect the **Fields tab** on the right panel with the default samples.  Invoice does schema-based extraction to extract fields relevant to the document type, such as **AmountDue**, **BalanceForward** and **Billing Address**. Note fields have a confidence score.
3. Hover over a field in the right panel, like "AmountDue.Amount" value. Notice that it shows grounding to the document.
4. Now upload the same **towing-invoice.pdf** document to see how the schema-based extraction applies to your own file. Compare the extracted fields and confidence scores with the layout extraction results you've got in the previous step to understand the differences.

> [!Note] **Layout and fields:** Use Layout to inspect how a document is organized, and an invoice schema to retrieve named business values. A field such as **AmountDue** selects a specific meaning rather than returning every number on the page.

### Try out other prebuilts

Feel free to experiment with further prebuilt analyzers to understand how CU Studio handles different document types and extraction scenarios. Below you can find a few examples of prebuilt analyzers along with the sample documents provided in the data folder, and the fields they extract.

| Prebuilt in Studio | Upload | Inspect |
| :--- | :--- | :--- |
| Identity / Generic ID document | demo-id.pdf | Named holder and available ID-like fields. This fictional membership specimen is not a government ID. |
| US tax / 1099A | form-1099a.pdf | Tax year, lender, borrower, account, and form boxes. Nested year/copy results are not extra input documents. |

> [!Tip] To locate 1099A under the US tax category, select **More analyzers**, if not immediately visible in the list.

> [!Note] **Checkpoint:** you can explain the difference between document layout and schema-based extraction.

===

## Step 3: Build a custom analyzer

### Custom repair estimate analyzer 
In this step, we will build a custom repair analyzer to handle repair estimate documents specifically. This document is a lot like an invoice, but we need to add auto-specific fields like **VIN** and **odometer**.

> [!Note] For this step, you'll use the **gpt-5.5** model instance pre-provisioned and mapped by the lab template. 

1. Move from the **Discover** to the **Build** tab, by selecting it on the top right corner of the top navigation bar.
2. Click on **Create** to start building your custom repair analyzer.
3. Name the project as `custom-repair-extractor`.
4. Select `2026-06-01 (Preview)` as the API version and `Standard Extraction` as the workflow type.

!IMAGE[kke6gm3z.png](instructions359897/kke6gm3z.png)

5. Expand the **Advanced settings** section and check that **gpt-5.5** is selected as model. Leave the other parameters as default and confirm by selecting **Create**.

!IMAGE[jur6eyeq.png](instructions359897/jur6eyeq.png)
6. Once your project is created, select **Browse for Files** and upload `C:\Users\LabUser\Desktop\ignite26-LAB664\data\samples\repair-estimate.pdf`.
7. In the **Choose a template window**, select the **Invoice** one. Click on **Save** to proceed.
8. Add additional vehicle, vin, and odometer fields either with import or manually to configure the repair fields. 

> [+Note] **Import from JSON - repair fields**
>
> On the **Schema** tab, select **Import** (up-arrow icon) in the toolbar above the fields, between **Suggest** and **Export**, as highlighted below. Choose `repair-schema.json` from `data\samples`. Confirm schema replacement if prompted.
>
> !IMAGE[lqoeliv3.png](instructions359897/lqoeliv3.png)

> [+Note] **Enter manually - repair fields**
>
> Keep all Invoice template fields. Add the three fields below, with method **Extract**, one by one. Enter each **Name**, **Type**, and **Description** before adding the next field.
>
> !IMAGE[y1l65rn4.png](instructions359897/y1l65rn4.png)
>
> | Field | Type / method | Copy this description |
> | :--- | :--- | :--- |
> | `vehicle` | String / Extract | `Printed vehicle name as one string, including year/make/model when present. Do not add color, decode the VIN, or infer missing details.` |
> | `vin` | String / Extract | `Exact value explicitly labeled VIN. Do not correct it or substitute registration, plate, or account numbers. Leave unset if absent.` |
> | `odometer` | Number / Extract | `Printed Odometer or Inspection Mileage as a number. Remove grouping separators; no units. Do not substitute Annual Mileage or infer an absent value.` |

> [!Note] **Field names and descriptions instruct the model:** Names and descriptions act like "mini-prompts" instructing the LLM how to interpret the document. For example, naming the intended entity, likely printed label, and exclusions helps distinguish a vehicle VIN from other identifiers.

9. After either path, verify the three vehicle fields and the retained Invoice fields, then select **Save**.
10. **Run analysis:** Click the **Run analysis** button in the upper-left corner to test the updated analyzer.

!IMAGE[ctdjrztc.png](instructions359897/ctdjrztc.png)

11. In the analysis results, verify the saved schema contains the three fields above: `vehicle = "2019 Toyota Corolla LE"`, `vin = "5YFEPMAE3KA513905"`, `odometer = 94360`. The repair proposal total is $1,310.13. 
12. After the test passes, click on **Build analyzer** to turn your tested extraction configuration into a reusable object. Name it `repair_extractor_analyzer` and optionally add a description. Select **Build** to complete the process.

!IMAGE[eli9ysmu.png](instructions359897/eli9ysmu.png)

13. Once you are prompted with 'Built successfully', your analyzer is ready for use. Click on **Jump to analyzer list** to verify the analyzer details. Close the window once done. You'll find your newly created analyzer in the **Analyzer list**.

!IMAGE[kd8y2urd.png](instructions359897/kd8y2urd.png)

> [!TIP] Double check the API version of the analyzer you just created is '2026-06-01-preview'. You won't be able to change it later, so you need to create a new analyzer with the correct API version otherwise.

===

## Step 4: Add a custom Statement analyzer with generative fields

Now let's work with a different kind of document: a statement about the incident. Unlike an invoice, a statement may describe the same damage in several places or leave important details unstated. You will use **Extract** for facts explicitly present in the document and **Generate** for a concise, grounded synthesis of the narrative.

Choose an import or manual entry, then inspect how the same seven field descriptions constrain the result.

1. Return to the **Build** tab -> **Project list** and create a second **Standard Extraction** project using the '2026-06-01 (Preview)' API version. Name it `custom-statement-extractor`. Expand the **Advanced settings** section and check that **gpt-5.5** is selected as model. Then select **Create**. 

!IMAGE[g5cz3r5i.png](instructions359897/g5cz3r5i.png)

2. Select **Browse for Files** and upload `packet-01-statement.pdf` from `data\samples`.
3. In the pop-up that appears after the document upload, keep **Document Analysis** as the selected template, disable **AI-Powered field suggestions**, then select **Save**.

!IMAGE[szpjguew.png](instructions359897/szpjguew.png)

4. Choose import or manual entry way to configure the Statement fields.

> [+Note] **Import from JSON - Statement fields**
>
> In the **field-schema toolbar**, select **Import** and choose `statement-schema.json` from `data\samples`. Confirm schema replacement if prompted.
>
> !IMAGE[03cudcq2.png](instructions359897/03cudcq2.png)

> [+Note] **Enter manually - Statement fields**
>
> In the **field-schema editor**, remove any template fields and add exactly these seven fields. 
>
> | Field | Type / method | Copy this description |
> | :--- | :--- | :--- |
> | `claimant_name` | String / Extract | `Name explicitly identifying the claimant or insured vehicle owner. Do not substitute a witness, other driver, adjuster, or recipient. Leave unset if unclear.` |
> | `incident_date` | Date / Extract | `Date the reported incident occurred, not the date the statement or email was written or sent. Leave unset if absent.` |
> | `incident_location` | String / Extract | `Location explicitly reported for the incident. Leave unset if absent.` |
> | `vehicle` | String / Extract | `Claimant vehicle as one string, including year, make, model, and trim when stated. Do not include color or the other vehicle. Do not infer unstated details.` |
> | `vin` | String / Extract | `Exact VIN explicitly stated for the claimant vehicle. Do not decode, correct, or infer it; leave unset if absent.` |
> | `reported_damage` | String / Generate | `Generate a concise description of damage reported by the claimant, combining mentions across the statement or email. Use only stated information. Do not present reported damage as inspected or verified, or infer damage, cause, fault, coverage, liability, or payment. Leave unset if no damage is reported.` |
> | `summary` | String / Generate | `Generate a concise summary of the claimant's narrative using only information in this statement or email. Preserve uncertainty and distinguish reported events from verified facts. Do not infer missing details, fault, coverage, liability, or payment.` |

After either path, verify **seven fields: five Extract and two Generate**, with **Source & Confidence** enabled.

> [!Note] **Extract and Generate:** Keep stated facts separate from generated interpretations. A **generated field** can summarize by combining passages and may not be a direct quotation from the document. **Extract** indicates the result should be pulled directly from a value in the document.

5. Click **Save**.
6. Click **Run analysis** to test the uploaded handwritten statement. Inspect the returned facts alongside the source document.
    - In the statement, check `claimant_name = "Danielle Ortiz"` and `incident_date = 2026-02-12`. The incident date should not be replaced by the letter's sent date.
    - The five *Extract* fields contain stated facts; the two *Generate* fields provide readable, grounded synthesis rather than verbatim quotes.
    - Inspect source highlights and confidence where returned. 
    - If a fact is not stated in the document, check that the analyzer leaves the corresponding field empty rather than guessing a value.

> [!Tip] 
> Make sure to disable the **Hide missing fields** toggle to view all fields, including those that are not populated in the current document.
>
> !IMAGE[33b9kcoj.png](instructions359897/33b9kcoj.png)

Next, test the same schema against a typed email:

1. Select **Browse for Files** and upload `C:\Users\LabUser\Desktop\ignite26-LAB664\data\samples\email-statement.pdf`. Then select **Run analysis**.
2. Perform the same checks as in the handwritten statement. 
3. After reviewing both documents, select **Build analyzer** and enter a new unique ID, for example `statement_extractor_analyzer`.  In the **Analyzer list**, you should now see two custom analyzers, as in the screenshot below.

!IMAGE[61ot591l.png](instructions359897/61ot591l.png)

> [!TIP] Double check the API version of the analyzer you just created is '2026-06-01-preview'. You won't be able to change it later, so you need to create a new analyzer with the correct API version otherwise.

> [!Note] **Checkpoint:** your custom repair and statement analyzers have both been tested and built, and you have recorded both analyzer IDs.

===

## Step 5: Split a claims packet using a classification analyzer

So far, you have analyzed one document at a time. An insurance submission usually contains several documents, often with different formats and multiple pages. In this step, you will create a classifier that identifies document types and splits a packet into logical documents before extracting any fields.

You will start with a small three-page packet, then test the same configuration against two larger packets. This will help you see the difference between a page boundary and a document boundary.

> [!Note] **Classification and splitting:** **Classification** identifies the document type based on a description. **Splitting** breaks the document into logical segments aligned with the categories.

### Create the classification project

1. Return to **Build** > **Project List** in CU Studio and create a new **Classification** project, named `packet_classifier`. Select API version **2026-06-01 (Preview)** and check that **gpt-5.5** is selected in **Advanced settings**.

!IMAGE[9maoqxjx.png](instructions359897/9maoqxjx.png)

2. In the new project, select **Browse for files**. Navigate to `C:\Users\LabUser\Desktop\ignite26-LAB664\data\samples` and upload `classification-packet.pdf`.
 
> [!Note] **Upload first:** the routing-rule editor becomes available after a file is uploaded.

3. Choose **one** way to configure the four categories. Do not assign child analyzer IDs yet.

> [+Note] **Import from JSON - classification rules**
>
> In the **Routing rules** tab, click the three-dot menu (⋮) immediately beside **Add category**, then select **Import**, confirm, and choose `classifier-config.json` from `data\samples`. This imports four categories and logical-document segmentation, with no extraction routes.

> [+Note] **Enter manually - classification rules**
>
> In **Routing rules**, add the four category keys and descriptions below. Enter each **Name** and **Description** before adding the next category. Leave every **Analyzer ID** empty.
>
> !IMAGE[7qhnpb5o.png](instructions359897/7qhnpb5o.png)
>
> | Category key | Copy this description |
> | :--- | :--- |
> | `id_document` | `The lab's identity-like demo card with named holder, portrait and membership identifier. This synthetic membership card demonstrates ID field extraction, not government-ID authenticity. Exclude invoice, tax and repair documents.` |
> | `tax_1099a` | `An IRS Form 1099-A Acquisition or Abandonment of Secured Property, including fictional borrower-copy examples. Exclude other tax forms and prose references.` |
> | `repair_estimate` | `A standalone repair workshop estimate or quote with vehicle details and proposed repair work. Keep continuation pages of the same estimate together; split a different estimate even if adjacent. Exclude towing/rental/glass invoices and their supporting inspection supplements even when they mention a proposed repair schedule.` |
> | `other` | `Each distinct supporting document: policy declarations/endorsements, claim intake forms, incident reports, handwritten statements, towing/rental/glass invoices with their own continuation supplements, valuation/downtime schedules, and workshop inspection records. Identify logical boundaries even when adjacent documents both have category other. Keep paginated continuation pages together; do not merge different document titles or identifiers. These documents are unrouted, not discarded.` |

After either path, verify **four categories and no routes**, then configure segmentation:

1. In **Routing rules**, turn on **Enable segment**, as shown below.

!IMAGE[11mmze7v.png](instructions359897/11mmze7v.png)

> [!Note] With the configured settings, a two-page rental invoice should remain one logical document. Two adjacent documents should still be separate, even when both belong to `other`.

2. Select **Save** and wait until saving indicators clear before changing tabs. Select **Run analysis** and remain in the project until it finishes. Inspect the results to ensure documents are segmented correctly.
3. Inspect details in **Test** tab. The **Segment** selector initially shows the retained parent, `input1`. Open it and select each `input1/segment...` entry to see its category and page range. Expect `id_document` on page 1, `tax_1099a` on page 2, and `repair_estimate` on page 3. Every page should be covered once. Classification-only child segments have **Result**, not domain analyzer fields.

!IMAGE[s51l89mw.png](instructions359897/s51l89mw.png)

### Test the full customer packet

In the previous step, you tested a small packet to ensure the classifier correctly segments individual documents. Now, you will test the full customer packet to verify the classifier's behavior on larger, multi-document files.

1. Within the same project, select again **Browse for Files** and upload `C:\Users\LabUser\Desktop\ignite26-LAB664\data\samples\packet-01.pdf`. 
2. Click on **Run analysis**. After it finishes, inspect each segment's category and page range in the uploaded packet. Use the authored document groups below as a reference for **packet-01.pdf**:

> [!Note] Page references use the PDF viewer's 1-based page numbers in the uploaded packet, not page numbers printed within individual documents or the segment number.

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

3. Check that continuation pages stay together, while different adjacent documents remain separate even when both belong to `other`. The statement and rental invoice are Other at this stage; they are unrouted, not discarded.

> [!Tip] You can easily check the pages assigned to each segment, by looking at the label below the segment name.
> !IMAGE[vcl16bde.png](instructions359897/vcl16bde.png)

4. Next, upload `packet-03.pdf` from the same folder and run analysis. Review its 13 pages in the uploaded packet. Unlike packet-01, this packet has separate repair estimates on pages 8 and 9 (`repair_estimate`), a statement on page 10 (`other`), and a towing invoice on page 11 (`other`). All other page ranges and categories match the table above.
5. Before moving to the next step, select **Build analyzer** and use a unique ID such as `packet_classifier`. Also include a description, for example, `Classifier for multi-document analysis`.
6. After the build succeeds, choose **Stay in the project** to continue.

> [!Note] **Checkpoint:** you can identify categories and logical page ranges in a mixed packet. No extraction routes have been assigned yet.

===

## Step 6: Extract fields from each segment of the packet

Continue in the editable step 5 project. If you left it, return to [CU Studio Build](https://contentunderstanding.ai.azure.com/build), open **Project list**, and open your project.

Choose **one** of the two configuration paths below (import or manual), then continue at [Verify, test, and build the router](#verify-test-and-build-the-router). Both paths finish with the same tests and build.

If you chose different custom IDs in steps 3-4, replace `repair_extractor_analyzer` and `statement_extractor_analyzer` in the imported rules' **Analyzer ID** selectors with your actual built IDs before saving. Use those same IDs for manual entry. Red **Analyzer not found** labels must be resolved before running.

> [+Note] **Import from JSON - extraction routes**
>
> In the **Routing rules** tab, click the three-dot menu (⋮) immediately beside **Add category**, then select **Import**, confirm, and choose `router-config.json` from `data\samples`. Do not use the field-schema Import button.
>
> !IMAGE[ywqnyvhk.png](instructions359897/ywqnyvhk.png)

> [+Note] **Enter manually - extraction routes**
>
> In **Routing rules**, retain `id_document` and `tax_1099a` with their step 5 descriptions. Select their routes below through **Analyzer ID** > **Prebuilt**. For tax, choose the unversioned `prebuilt-tax.us.1099A`.
>
> Update `repair_estimate` and `other` to the descriptions below, then add `statement`, `towing_invoice`, and `rental_invoice`. Select the built repair and Statement analyzers through **Custom**, and invoice routes through **Prebuilt**. Enter each category's name, description, and route before adding the next.
>
> !IMAGE[1b7s3xw7.png](instructions359897/1b7s3xw7.png)
>
> | Category key | Extraction route |
> | :--- | :--- |
> | `id_document` | `prebuilt-idDocument.generic` |
> | `tax_1099a` | `prebuilt-tax.us.1099A` |
> | `repair_estimate` | `repair_extractor_analyzer` |
> | `other` | **No route** |
> | `statement` | `statement_extractor_analyzer` |
> | `towing_invoice` | `prebuilt-invoice` |
> | `rental_invoice` | `prebuilt-invoice` |
>
> !IMAGE[ujvd6zg6.png](instructions359897/ujvd6zg6.png)
>
> | Category key | Copy this description |
> | :--- | :--- |
> | `repair_estimate` | `A standalone repair workshop estimate or quote with vehicle details and proposed parts/labor. Keep continuation pages of the same estimate together; split a different estimate even if adjacent. Exclude towing/rental/glass invoices and their supporting inspection supplements even when they mention a proposed repair schedule.` |
> | `other` | `Each distinct unrouted supporting document: policy declarations/endorsements, claim intake forms, incident reports, glass/panel service supporting records, valuation/downtime schedules, and workshop inspection records. Statements, towing bills, and rental billing belong to their named categories, not Other. Identify logical boundaries even when adjacent documents both have category other. Keep continuation pages together; do not merge different titles or identifiers. These documents are unrouted, not discarded. Exclude towing/recovery/security charge supplements; classify those as towing_invoice.` |
> | `statement` | `A handwritten or typed claimant statement or email describing the incident, claimant vehicle, and reported damage. Keep continuation pages of the same statement together. Exclude claim forms, incident reports, witness or other-driver accounts, and repair or invoice documents.` |
> | `towing_invoice` | `A towing or roadside-recovery invoice, bill or charge ledger for vehicle transport, storage or release. Keep continuation and release/custody supplements from the same bill together. Payment may be unpaid or pending; do not infer payment. Exclude repair estimates, rental billing, and glass or panel service quotes. Include towing/recovery/security charge supplements that list service charges or a total due, even when they also contain inspection details or repair-quote references.` |
> | `rental_invoice` | `A vehicle rental billing document or invoice with rental agreement references, dates or daily charges. Keep the same agreement's pickup/billing/vehicle-condition continuation pages together. Payment may be unpaid or pending; do not infer payment. Exclude towing bills, repair estimates, and glass or panel service quotes.` |


### Verify, test, and build the router

Continue here after either manual configuration or import.

1. Verify there are **seven categories and six assigned routes**, with no route for `other`. Keep **Enable segment** on, as in step 5.

!IMAGE[bj0sbmti.png](instructions359897/bj0sbmti.png)

2. Select **Save** and wait until saving indicators clear.
3. Select the existing **classification-packet.pdf** thumbnail, then **Run analysis**. Wait for completion before inspecting results or selecting another file.
4. In **Test**, expand the segments dropdown and select the child content you want to inspect (e.g. input1/segment1), then open **Fields**.
!IMAGE[6cp63e2r.png](instructions359897/6cp63e2r.png)

> [!Note] The parent `input1` is not the child analyzer's field view. 

Inspect ID fields on segment 1, nested 1099-A fields on segment 2, and custom `vehicle`, `vin`, and `odometer` fields on segment 3. The tax route adds nested year/copy segment entries; select the nested entry with a **Fields** tab. These are not extra input documents. Select a field label to inspect its source highlight.
5. Replicate the same process for the other 2 files:
   - Select **packet-01.pdf** and run analysis. Check categories and page ranges against the authored groups in step 5, then inspect repair on page 8, the Statement route on page 9, and the rental invoice across pages 10-11. The statement and rental invoice now have their named categories and child fields rather than belonging to Other. Check that the rental continuation remains part of the same invoice.
   - Select **packet-03.pdf** and run analysis. Inspect the Statement route on page 10, and the towing invoice on page 11, along with the other categories and logical boundaries. Check invoice amounts against the towing supplement's **$237 charge** on page 11, not the separate **$1,699.04 repair quote** it references. Other documents remain in the parent content without a domain extraction route.
6. Compare returned fields with their source documents. Keep claimant-reported details distinct from verified facts, and proposed repair amounts distinct from invoiced charges or proof of payment. If a fact is not stated, check that its field is unset rather than invented; turn off **Hide missing fields** to see fields marked **Not found**.
7. After reviewing all three packets, select **Build analyzer** with a new unique ID, such as `router_analyzer`. Do not overwrite the classification-only analyzer you created in the previous step. After a successful build, use **Jump to analyzer list**. Verify this exact analyzer has status **Ready**. Record its ID and your resource endpoint for later use.

> [!Note] **Checkpoint:** a tested, ready router links every non-Other category to extraction.

===

## Step 7: Evaluate results with the Insurance Workbench app

### Part 2: Validate the data

In this step, you will move from authoring analyzers to reviewing their results in an application. The Insurance Workbench loads ten customer packets, totaling 118 pages, from `data\packets` ; you do not need to upload them manually.

The app automatically loads the included cached extraction results and policy reviews. Use it as a results viewer: inspect the collection, review **Business rules validation** results, and follow policy findings back to their evidence. Later, you will explicitly rerun one repair estimate and can ask the policy agent follow-up questions.

### Launch the app

1. Return to the PowerShell window you used in [step 1](#step-1-environment-setup). Confirm both setup commands completed successfully and **Deploy** reported `Workbench configuration activated`.
If it is still running, wait for it to finish. 
- If either command failed, resolve the reported error and rerun that command successfully before continuing.

2. Launch the separate app and keep this terminal open:

   ```PowerShell
   powershell -ExecutionPolicy Bypass -File .\infra\launch-workbench.ps1
   ```

3. Open +++http://127.0.0.1:8791/+++ in a new browser tab. Do not open `workbench.html` directly.

Wait for the cached results to load. Opening the app or switching review tabs does not submit a new analysis. The setup in step 1 prepares the connection needed for the repair rerun in step 8 and follow-up chat in step 9.

> [!Note] To stop the app at any time, return to PowerShell and press **Ctrl+C**.

### Explore the included results first 

1. Start with analyzing results on **Parse and extract** -> **Classification** (your default selection when the app starts, no action needed). The cached results load automatically; wait until the **Cached** badge and all ten customer rows appear.  
2. Each row is one customer; each check is a returned document instance and page range. Click a check or field value to open its full source PDF at that page. Documents classified as `other` are not shown in this grid, but remain in the analyzer's full response.
3. Switch to the **ID**, **1099-A**, **Repair Estimate**, **Statement**, **Towing Invoice**, and **Rental Invoice** views. Select a returned value to inspect its source document.
4. Turn on **Confidence** to inspect returned scores. Blank means the service omitted a score, not zero. Click line items for source boxes or their table icon to expand item rows below the customer.

> [!Note] **Confidence and grounding:** Confidence scores and source highlights are additional features created by CU for fields where these features are enabled. Confidence scores help identify low-confidence results for review. Source grounding shows where in the Markdown or PDF the value came from.

===
## Step 8. Evaluate results with business rules validation

Evaluation with **Business rules validation** uses fixed rules to check the consistency of the results. In this exercise, use the included repair error to identify an issue with the analyzer, improve it in CU Studio, and compare results.

1. Select **Business rules validation**. The matrix contains exactly three fixed extraction checks:
    - **Total Amount, SubTotal, Tax verification** asks whether SubTotal plus tax equals Total Amount.
    - **Repair line items, SubTotal verification** asks whether repair line-item amounts sum to the explicit SubTotal.
    - **Multiple Estimates Warning** warns when repair-estimate totals differ. It shows each shop and quote amount with a source link. This is a review warning, not proof of an extraction error.
2. Select the red **Error** for packet 8, under **Repair line items, SubTotal verification**. 

!IMAGE[hs9rqs9w.png](instructions359897/hs9rqs9w.png)

The original Repair Estimate result shows the calculation `USD 980.00 + 124.00 + 0.00 = 1104.00; Subtotal = 1600.00`. Review the explanation and the formula fields, then select the source or formula to highlight the native values in the PDF.

### Part 3: Fix the validation issue

You've identified the missing labor amounts. Now change the analyzer, test the fix, and check the same failure again.

3. Go back to **CU Studio** and reopen the editable custom **Repair Estimate** extraction project from step 3, `custom-repair-extractor`. Do not edit the packet router or classification project: this rerun requires a ready single-document repair analyzer.
4. Choose **one** way to update the repair field schema.

The PDF lists parts and labor separately, matched by operation reference. The original extraction copied only the parts amounts into the row totals, leaving out labor. Use **Extract** for `PartsAmount` and `LaborAmount` to read those printed values, and **Generate** for `TotalAmount` to calculate their sum, which is not printed as a single row total. This makes the intended calculation explicit; the independent subtotal check still verifies the result.

> [+Note] **Import from JSON - repair fix**
>
> On the **Schema** tab, select **Import** (up-arrow icon) in the main toolbar above the fields, between **Suggest** and **Export**, as highlighted below. Use the main Schema toolbar, not the nested line items editor. Choose `repair-fixed-schema.json` from `data\samples`. Confirm schema replacement if prompted. It retains the full step 3 invoice and vehicle schema, changing only `LineItems.TotalAmount` and adding `LineItems.PartsAmount` and `LineItems.LaborAmount`. If you added your own fields beyond step 3, use the manual path instead to retain them.
>
> !IMAGE[rmt8l9rr.png](instructions359897/rmt8l9rr.png)

> [+Note] **Enter manually - repair fix**
>
> In the **Schema** fields list, find **LineItems** and select its grid icon to open the line items editor.
>
> !IMAGE[spqympsb.png](instructions359897/spqympsb.png)
>
> Within **LineItems**, delete the existing **TotalAmount** object using the trash can icon on its row. This also removes its nested **Amount** and **CurrencyCode**. Do not delete or change the separate document-level **TotalAmount**.
>
>
> Add these three fields directly under **LineItems**, as siblings of **Description** and **Quantity**, not inside another object:
>
> | Field | Value type | Method | Copy this description |
> | :--- | :--- | :--- | :--- |
> | `PartsAmount` | Number | Extract | `Printed parts amount for this line item's operation reference. Match the same operation across parts and labor sections. Do not substitute labor, a unit price, or a subtotal. Leave unset if absent; an explicit zero is valid.` |
> | `LaborAmount` | Number | Extract | `Printed labor amount for this line item's operation reference. Match the same operation across parts and labor sections. Do not substitute parts, labor hours, a rate, or a subtotal. Leave unset if absent; an explicit zero is valid.` |
> | `TotalAmount` | Number | Generate | `Total amount for this line item. Use its explicit printed total; otherwise, sum PartsAmount and LaborAmount. Do not use a parts-only amount or the invoice subtotal. Leave unset if no line-item total is printed and either component is missing.` |
>
>
> Add the fields in this order, then select **Back to main view**.

After either path, verify the document-level **TotalAmount** is unchanged and **LineItems.TotalAmount** is now a single **Number**, not an object.

!IMAGE[ljfsfbut.png](instructions359897/ljfsfbut.png)

Select **Save**. The validation rule supports both the numeric row total and the original `TotalAmount.Amount`. It prefers the returned row total and uses parts plus labor only when that total is missing; a wrong returned total still fails.

5. To verify the changes, select **Browse for files** and upload `packet-08-estimate.pdf` from `data\samples`, then select **Run analysis**. Expand the **LineItems** object in the **Test** tab and inspect every line item and its source regions. A useful result for this document is:

   | Line item | PartsAmount | LaborAmount | TotalAmount |
   |---|---:|---:|---:|
   | 1 | 980.00 | 223.20 | 1203.20 |
   | 2 | 124.00 | 62.00 | 186.00 |
   | 3 | 0.00 | 210.80 | 210.80 |

   The explicit `SubtotalAmount` is `1600.00`. Inspect the extracted parts and labor source regions; a generated total may not have its own source box. These values reconcile, but always verify the native Studio result rather than assuming a model run is deterministic.

> [!Note] **Derived totals:** Treat a generated line-item total as a calculation, not newly printed source text. Verify its extracted parts and labor inputs against the PDF, then reconcile the rows with the independent subtotal. Arithmetic consistency alone doesn't prove every extracted value is correct.

6. Save and build the updated project by clicking on **Build analyzer** and pick a new unique analyzer name, like `custom_repair_analyzer_v2`. Add a description too, such as `Updated repair analyzer with parts and labor amounts`. Wait until the analyzer is **Ready**, then copy its analyzer name exactly. 
7. Return to the packet-8 error in the **Insurance Workbench app**, enter the new analyzer name in **Updated repair estimate analyzer name**, and select **Rerun**. This submits only packet 8's individual repair estimate as a fresh, billable CU call; there is no second confirmation dialog.

!IMAGE[z71i70zd.png](instructions359897/z71i70zd.png)

8. While the spinner is active, wait for the rerun to finish. The updated result appears below the original with its own status and calculation. Its field table shows formula inputs plus returned `PartsAmount` and `LaborAmount`, grouped by numeric line-item index in the order total, parts, labor, followed by SubTotal. Select the original and updated results to compare their own source boxes. A successful updated result should show `USD 1203.20 + 186.00 + 210.80 = 1600.00 (Subtotal)` and change the check to **Pass**.

!IMAGE[tha6s6rr.png](instructions359897/tha6s6rr.png)

9. The rerun preview is temporary and browser-only. It is not written to the saved extraction cache or native JSON. Navigating within the current run keeps the original and latest updated result; another rerun replaces the previous preview. Refreshing the page or changing runs clears it. If the source cannot be matched to one individual PDF, return to Studio and correct the router's document boundaries before rerunning.

===

## Step 9 - Optional: Review claims with Azure AI Search (Foundry IQ)

Step 8 used fixed business rules. In this optional part, use Azure AI Search (Foundry IQ) retrieval and Agent Framework to compare claim facts with policy evidence. The agent queries a Search index directly, not a knowledge-base API.

!IMAGE[bsv08s9h.png](instructions359897/bsv08s9h.png)

The app starts with saved policy reviews and native document previews; inspecting them doesn't run ingestion again. Historical saved evidence can use CU Layout, while the managed deployment in step 1 uses Search-managed Standard extraction. A saved review isn't a newly executed policy check.

If you're starting here and the app isn't running, follow [Step 7's app-launch instructions](#launch-the-app), then open +++http://127.0.0.1:8791/+++.

1. Open **Check policies**. The customer grid contains **Daily rate**, **Effective terms**, and **Repair estimate** checks.
2. Select the **Policy documents** link to open a folder containing the indexed documents in File Explorer. These documents are already indexed; no upload is needed.

### Follow claim facts to the policy evidence

3. In the **#1 Danielle Ortiz** row, select the result under **Daily rate**. Compare the **Claim** and **Policy** values in the right panel. Select the linked claim amount "54 USD/day" to inspect its source files from the claim. Then select **Back to policy check**.

!IMAGE[uf89wmrn.png](instructions359897/uf89wmrn.png)

4. Select the linked policy daily limit "$75/day base charge" to open the **Original** declarations that the agent found in Azure Search. Inspect the **Rental limit** column. Switch to **Prebuilt Search** to see the searchable representation created by Content Understanding as part of Azure Search standard content extraction.

!IMAGE[9n46bxvj.png](instructions359897/9n46bxvj.png)

5. Inspect the searchable text, tables, and page references in **Prebuilt Search**. The lab's managed Search deployment uses [Content Understanding](https://learn.microsoft.com/azure/search/cognitive-search-skill-content-understanding) standard content extraction; the pipeline also enables semantic chunking and AI-generated figure descriptions. Then select **Back to policy check**.

### Inspect figure-backed repair guidance

6. In the **#2 Victor Bennett** row, select the result under **Repair estimate**. Compare the gross repair total with the retrieved Washington routine-review threshold, rather than an arithmetic rule from step 8.

!IMAGE[91ysxon6.png](instructions359897/91ysxon6.png)

7. Select the linked policy threshold to inspect the original supporting diagram. In **Prebuilt Search**, compare the searchable figure description and flowchart text with that original; the saved representation is evidence to inspect, not proof of a newly rendered diagram. Then select **Back to policy check**.

!IMAGE[2ihrasgl.png](instructions359897/2ihrasgl.png)


### Ask a follow-up question

8. For the selected **Repair estimate** check, select **Ask agent**. Enter a follow-up such as `What is the routine repair-review threshold if this incident were in Arizona?` Sending it allows you to use the agent to get additional clarification.

!IMAGE[ckohd4yo.png](instructions359897/ckohd4yo.png)

---

===

## Step 10 - Optional: Use GitHub Copilot + CLI to improve your analyzer

In this optional exercise, you'll see how:

- The Content Understanding CLI (`azd ai cu`) lets you or a coding agent manage analyzers and analyze documents.
- Copilot can turn a natural-language request into an improvement workflow: inspect the analyzer, make targeted schema changes on a copy, and compare before/after results.

You'll repeat the repair-analyzer workflow from Step 8 using separate baseline and improved analyzers. Your original analyzers and Workbench results stay unchanged.

### Install the Content Understanding CLI

Open a separate **Windows PowerShell** window. With Azure Developer CLI (`azd`) 1.37.0 or later already available on the lab VM, run:

```PowerShell
azd ai cu
```

When `azd ai cu` prompts, press **Enter** to install `azure.ai.content-understanding`. Then run:

```PowerShell
azd ai cu --help
azd auth login
```

Sign in with the same Azure lab account used in CU Studio.

### Sign in to the GitHub Copilot app

1. In your browser, navigate to GitHub enterprise sign-in at `https://github.com/enterprises/skillable-events/sso` and sign in with your **Azure lab credentials**.
2. Open the **GitHub Copilot app** from the Desktop icon and select **Sign in to GitHub**. On the **Device Activation** page, confirm your lab GitHub account is shown under **Signed in as**, then select **Continue**. If needed, select **Use a different account** first. Enter the one-time code, then authorize the GitHub Copilot app when prompted to complete sign-in.
3. If the **Connect your work** screen appears, select **Choose a folder...**, choose `C:\Users\LabUser\Desktop\ignite26-LAB664`, then select **Continue**. Use the existing lab folder, not a sample repository.

!IMAGE[3yuvq4zf.png](instructions359897/3yuvq4zf.png)

### Open a session for the lab folder

1. If `ignite26-LAB664` is not already listed under **Sessions**, select **+** beside **Sessions**, then select **Add local folder or repository**. Choose `C:\Users\LabUser\Desktop\ignite26-LAB664` in the folder picker.

!IMAGE[93smfl0y.png](instructions359897/93smfl0y.png)


2. Select **+** beside **ignite26-LAB664** under **Sessions** to create a **New session**. Expand the folder first if needed.

!IMAGE[hb4zznz1.png](instructions359897/hb4zznz1.png)

3. Confirm the folder label below the prompt shows **ignite26-LAB664**. Clicking this label opens the folder picker; leave the lab folder selected.

!IMAGE[mvfucsce.png](instructions359897/mvfucsce.png)

4. Keep **Interactive** mode and normal tool approvals enabled; do not enable **allow-all**.

!IMAGE[z2u8u7u0.png](instructions359897/z2u8u7u0.png)

5. Open the model picker in the prompt footer and select **GPT 6.1 Sol**. Leave reasoning effort at the lab default, **Medium**.

!IMAGE[spt098x3.png](instructions359897/spt098x3.png)

### Give the agent the task

Use `repair_extractor_analyzer` from **Step 3**, not the router or the improved analyzer from Step 8.
If you chose a different ID in step 3, substitute it in the prompt below.

> `Hey, I just validated packet 8 and the repair line items don't add up to the subtotal. Use data\documents\packet-08\05-estimate.pdf. Can you try fixing it on a copy of repair_extractor_analyzer? Add PartsAmount and LaborAmount as extracted numbers, and change the line-item TotalAmount from an object to a generated number. Use the printed row total if there is one, otherwise add parts and labor when both are there. Don't guess missing amounts, and leave the document total alone. Show me what you'll change first, then compare before and after.`

Copilot checks your Azure connection and asks for your Content Understanding endpoint if needed. Follow how Copilot turns your request into analyzer checks, CLI commands, a schema diff, approvals and a before/after comparison, not just the final answer. Review each CLI command in chat before approving it, then check the result.

If **Trust the ignite26-LAB664 repository?** appears, confirm this is the lab folder you selected, then choose **Always trust ignite26-LAB664**.

!IMAGE[ilc1ga19.png](instructions359897/ilc1ga19.png)

Review Copilot's initial proposal before approving a baseline analyzer copy and **two analyses** of `data\documents\packet-08\05-estimate.pdf`: one using the baseline copy and one using a separately approved improved analyzer.

!IMAGE[lt1mzyc6.png](instructions359897/lt1mzyc6.png)

Example approval prompt; wording may vary.

Copilot runs the first analysis with the baseline copy, then shows the proposed schema changes. It asks for a second approval to create a separate improved analyzer. Review the changes and approve to continue. Copilot then tests the improved analyzer and compares the results.

### Review the comparison

Explicitly extracting labor alongside parts helps the analyzer account for both when generating line-item totals. For packet 8, check that the line items now reconcile with the subtotal, while the document total remains **1,691.08**.

Copilot has created separate baseline and improved analyzers. In [Content Understanding Studio](https://contentunderstanding.ai.azure.com/), select your lab resource and look for the analyzer beginning with **copilot_repair_improved_** in **Analyzer list**. Copilot provides its full name in the results.

### More prompts to try

Stay in the session that ran the analyzer work. The first prompt needs approval for **four new document analyses**. The second uses saved results only.

**Check other packets**

> `Can you try data\documents\packet-01\05-estimate.pdf and data\documents\packet-03\05-estimate.pdf with both analyzers? Check if the fix changed anything else, like the vehicle, VIN or odometer. Show me the files and ask before running the four analyses.`

Use the individual repair estimates, not the full packets. Changed values are potential regressions to review, not proof that either result is correct.

**Review the changes - no new Azure calls**

> `Other than the amounts we fixed, did anything change or go missing? Show me the old and new values using the saved results. Don't run anything again.`

===

## Summary

Congratulations! You have successfully completed the lab.

In this lab, you explored how to turn insurance documents into structured, source-linked information for claims review. You:

- Compared layout extraction with prebuilt schema-based analyzers.
- Customized repair estimate and Statement analyzers, then classified, split and routed mixed document packets.
- Used the **Insurance Workbench app** to inspect extracted fields, review business-rule findings and compare an updated repair analyzer with the original.

If you completed the optional parts, you also applied policy evidence through **Azure Search (Foundry IQ) and Agent Framework**, or used \*\*GitHub Copilot and `azd ai cu`\*\* to improve a disposable analyzer copy with explicit approvals.
