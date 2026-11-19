<a name="start-building"></a>

<p align="center">
<img src="img/banner-ignite-26.png" alt="Microsoft Ignite 2026" width="100%"/>
</p>

# [Microsoft Ignite 2026](https://ignite.microsoft.com)

## 🔥LAB664: Build agentic document workflows with Content Understanding
### Session description

Enterprise processes start with unstructured content—documents, images, audio, video, emails. Before AI agents can act, they must understand and structure it. In this hands-on lab, use Azure Content Understanding (CLI, SDKs) in an agent loop to build an end-to-end workflow. Process real business content, extract and classify information, and route work through automated decision paths. Learn confidence-based automation and human-in-the-loop review for straight-through processing.

### 🚀 Getting started

#### View the session decks

The browser-ready **LAB664** and **BRK245** sessions have phone-friendly, scrollable
reading editions with inline demo videos and PowerPoint downloads. The original
animated slides and unedited notes remain available through **View animated slides**.
The LAB664 reading page links directly to the lab instructions.
After [GitHub Pages is enabled](slides/web/README.md#publish-on-github-pages),
view the [deck gallery](https://microsoft.github.io/ignite26-LAB664/),
[LAB664](https://microsoft.github.io/ignite26-LAB664/lab664/), or
[BRK245](https://microsoft.github.io/ignite26-LAB664/brk245/).
These links become available after the first successful Pages deployment.
GitHub's repository file viewer shows HTML source, not a running presentation.
For local viewing and publishing details, see the [deck guide](slides/web/README.md).

Follow the [nine-step lab guide](instructions/lab.md) for both guided and
self-paced sessions in the provisioned lab environment.
The guide covers Content Understanding extraction in CU Studio,
then policy checks in the separate Insurance Workbench App.
Lab-platform variables and VM screenshot paths in the guide are resolved
by the lab environment, not by GitHub's Markdown preview.

#### Set up or update the workbench

On Windows, install **Python 3.10 or later** with pip and venv. In PowerShell
at the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\setup.ps1
powershell -ExecutionPolicy Bypass -File .\infra\launch-workbench.ps1
```

Setup restores the locked npm packages, including **Deep Chat**, and installs
the **Python Microsoft Agent Framework** and Azure Search dependencies into
`.tools\policy-venv`. It installs a supported Node runtime and Azure CLI if
needed, but doesn't sign you in or create cloud resources. Stop the app and
rerun setup after pulling updates; no individual package installs are needed.
For managed package mirrors or a specific Python path, see
[`infra/README.md`](infra/README.md#lab-machines-with-package-mirrors).

Open [http://127.0.0.1:8791/](http://127.0.0.1:8791/). Keep the launch terminal
open. The included extraction and policy results work without Azure setup,
credentials or network access to Azure. Sign in with `az login` and prepare
the index configuration only to run live analysis or policy checks.

#### Try the policy-check comparison

On first launch, the app automatically loads the included **10/10** CU run and
all **30** saved policy checks. Open **Check policies**; grounded Search retrieval
is the default, with no retrieval selector. **Settings** > **Reload policy reviews**
reloads them; no separate extraction step is needed.
**Settings** > **Reload saved results** also loads the included CU run
independently. Without compatible local reviews,
the app reads all ten synthetic reviews directly from the checked-in demo bundle.
No restore command, Azure configuration or credentials are needed. **Bundled demo**
identifies these read-only results and their original Search index; they aren't
presented as results from a newly configured index. Existing local configuration
and caches aren't overwritten. Live-compatible cached results take precedence.
Loading makes no Azure calls. Follow-up chat requires live Azure configuration, but viewing the saved checks doesn't.
FoundryIQ is the lab's umbrella label; this implementation retrieves evidence
directly from Azure AI Search, not a Foundry IQ knowledge base.
The index name above the grid links directly to its Azure portal index view.
It follows the configured live agent index when available, or identifies the saved
review index otherwise. **Policy documents** opens the original policy PDFs folder
directly in Windows Explorer on the local workbench; opening errors appear beside
the link.
Select a policy check's source link to view its **Original**, **CU Search**, or **Digital parse** tabs.
Both native analyzer outputs are included for every active PDF; viewing them
needs no Azure sign-in or calls. Digital parse can legitimately contain no text
on a scanned PDF; the viewer explains that result without substituting OCR.

Under **Claim policy checks**, the three columns are **Daily rate**,
**Effective terms**, and **Repair estimate**, in that order.
Compare the claimed daily rental base rate with the effective cap for the matched
insured vehicle, and the applicable policy and genuine amendment with the actual loss date.
Match the policy ID and insured VIN, not just a similar vehicle.
**Repair estimate** independently compares each relevant distinct quote's gross total,
including stated tax and before deductible or payments, with the synthetic internal
state-specific routine review threshold retrieved from the repair-authority diagram.
This threshold isn't law, a contractual coverage cap or payment approval.
Different quote amounts alone don't require review here; **Business rules validation**
retains its separate multiple-estimates warning.
Compare the claim and policy
values in the right panel, then follow a value's source link to its PDF.
A check mark means **Satisfied**, an open circle means **Review required**,
and a circular-arrow icon means **Waiting for info**, not an agent still running.
**N/A** can apply to **Daily rate** for a confirmed non-rental
claim; **Effective terms** still compares the matched terms with the loss date,
and **Repair estimate** remains independent of rental applicability.
Packet **01** illustrates why a numerical rate fit is conditional on rental
eligibility, not payment approval. Packet **02** compares $61/day with its
$85 contractual cap. Missing unrelated repair completion
or insurer payment authorization doesn't create a wait for these narrow checks.
Linked page text is labeled as first-pass parsed evidence: its interpretation
isn't a typed CU fact, and no source boxes are invented.
These are evidence-based reviews, not coverage or payment approval.
Keep Texas's **$75/day** and Washington's **$85/day** contractual rental limits
separate from repair review authority; inspect the matched policy evidence for each.

In **Settings**, enable live calls, then select **Run live policy checks** and
confirm only to request policy work. Matching current
reviews are reused; uncached packets use scoped typed Parse fields and retrieved
policy evidence for each check, without claim-summary preparation or claim CU
reanalysis. Before three parallel comparison calls, the agent interprets rental
applicability for Daily rate using saved fields and selected first-pass page text.
Azure charges apply.
The previous three-, four-, and five-check bundles remain history; the new bundle replaces
the active results without editing extracted facts or inventing outcomes.
The active corpus contains 10 declarations, nine scanned effective-date records,
the issued Texas amendment and the two-page synthetic repair-review diagram.
The 21 legacy rental-terms/SOP PDFs remain under
`data\policies\archive\legacy-rental-review-v2\` with verified historical source aliases;
they aren't ingested or used by the current checks.
See [policy checks](docs/policy-checks.md) for the walkthrough and cache details.

For guided and self-paced sessions, follow
[step 9: compare policy checks](instructions/lab.md#step-9-review-claims-with-azure-search-foundry-iq).
Optional under-the-hood guidance covers the deployed Search index, policy PDFs,
Blob ingestion and the Agent Framework implementation. This PR uses an ordinary
Search index directly, not a Foundry IQ knowledge base.

**Lab owners:** a fresh clone doesn't include the machine-local policy
configuration. Complete [policy index setup](docs/policy-setup.md) before running
live work in the session; the bundled demo doesn't need it. The existing CU Layout index remains valid while optional managed
Standard ingestion prerequisites are unresolved; don't label it Standard.
Use [`infra/deploy.ps1`](infra/README.md#deploy-infrastructure-and-the-policy-index)
to run Search-managed Standard indexing with semantic chunks and AI figure descriptions.
Pass `-ResourceGroup` to discover existing lab services and configure the index
without a hand-filled settings file. ARM deployment requires the explicit
`-DeployResources` switch and a provisioning identity with role-assignment permissions.
Successful deployment also prepares the claim analyzer and writes the workbench's
verified runtime configuration, so no separate activation command is needed.
The setup notebook also walks through managed ingestion on the existing Search service.

### 🎯 Learning outcomes

By the end of this session, you will be able to:

- Extract structured, source-linked facts with prebuilt and custom Content Understanding analyzers.
- Classify and split insurance packets and route documents to extraction analyzers.
- Evaluate extracted claims with business rules, grounded policy checks, and human review.

### 💻 Technologies used

- Azure Content Understanding
- Azure Document Intelligence
- Microsoft Foundry
- Azure AI Search
- Microsoft Agent Framework

### 📚 Continue your learning

Pick your next step based on your learning style:

| Resource | What you'll get |
|----------|-----------------|
| **[Ignite 2026 Next Steps](https://aka.ms/ignite26-next-steps)** | Additional session repos and materials from Microsoft Ignite 2026 |
| **[Microsoft AI Skills Navigator](https://aka.ms/ignite26-asn)** | Discover AI skills, learning paths, and resources for your next step |
| **[Microsoft Learn](https://aka.ms/ignite26-learn)** | Official documentation and guided learning paths on these topics |
| **[Microsoft Foundry Community](https://aka.ms/MicrosoftFoundryDiscord-Ignite26)** | Connect with other learners and experts in our Discord community |

### 🌟 Microsoft Learn MCP server

The Microsoft Learn MCP Server gives your AI agent direct access to Microsoft's official documentation — grounded, up-to-date answers about the topics in this session.

**GitHub Copilot CLI** — Install with:

```shell
copilot plugin install microsoftdocs/mcp
```

**VS Code** — One-click install:  
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_Microsoft_Learn_MCP-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=microsoft-learn&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Flearn.microsoft.com%2Fapi%2Fmcp%22%7D)

For more information, visit the [Learn MCP Server repo](https://aka.ms/learnmcp).

### 👥 Content owners

<table>
<tr>
    <td align="center"><a href="https://github.com/jfilcik">
        <img src="https://github.com/jfilcik.png" width="100px;" alt="Joe Flick"/><br />
        <sub><b>Joe Flick</b></sub></a><br />
            <a href="https://github.com/jfilcik" title="talk">📢</a>
    </td>
    <td align="center"><a href="https://github.com/anatolip">
        <img src="https://github.com/anatolip.png" width="100px;" alt="Anatoly Ponomarev"/><br />
        <sub><b>Anatoly Ponomarev</b></sub></a><br />
            <a href="https://github.com/anatolip" title="talk">📢</a>
    </td>
    <td align="center"><a href="https://github.com/carlotta94c/">
        <img src="https://github.com/carlotta94c.png" width="100px;" alt="Carlotta Castelluccio"/><br />
        <sub><b>Carlotta Castelluccio</b></sub></a><br />
            <a href="https://github.com/carlotta94c/" title="talk">📢</a>
    </td>
    <td align="center"><a href="https://github.com/krishnakumar-muthukrishnan">
        <img src="https://github.com/krishnakumar-muthukrishnan.png" width="100px;" alt="Krishnakumar Muthukrishnan"/><br />
        <sub><b>Krishnakumar Muthukrishnan</b></sub></a><br />
            <a href="https://github.com/krishnakumar-muthukrishnan" title="talk">📢</a>
    </td>
</tr></table>

### ⚖️ Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.

Any use of third-party trademarks or logos are subject to those third-party's policies.
