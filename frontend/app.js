const state = {
    topic: "",
    search: "",
    reader: "",
    report: "",
    critic: "",
};

const elements = {
    topic: document.getElementById("research-topic"),
    run: document.getElementById("run-research"),
    searchResults: document.getElementById("search-results"),
    readerResults: document.getElementById("reader-results"),
    searchSubtitle: document.getElementById("search-subtitle"),
    readerSubtitle: document.getElementById("reader-subtitle"),
    report: document.getElementById("report-content"),
    download: document.getElementById("download-report"),
    scroll: document.getElementById("scroll-to-report"),
    statusBanner: document.getElementById("status-banner"),
    statusTitle: document.getElementById("status-title"),
    statusMessage: document.getElementById("status-message"),
    score: document.getElementById("critic-score"),
    strengths: document.getElementById("critic-strengths"),
    improvements: document.getElementById("critic-improvements"),
    verdict: document.getElementById("critic-verdict"),
    toast: document.getElementById("toast"),
};

const stepKeys = ["search", "reader", "writer", "critic"];

function setPipelineStep(key, status) {
    const step = document.querySelector(`.pipeline-step[data-step="${key}"]`);
    if (!step) return;

    step.classList.remove("running", "done");
    if (status) step.classList.add(status);
}

function resetPipeline() {
    stepKeys.forEach((key) => setPipelineStep(key, ""));
}

function setStatus(title, message, visible = true) {
    elements.statusTitle.textContent = title;
    elements.statusMessage.textContent = message;
    elements.statusBanner.hidden = !visible;
}

function showToast(message, isError = false) {
    elements.toast.textContent = message;
    elements.toast.classList.toggle("error", isError);
    elements.toast.classList.add("show");

    window.setTimeout(() => {
        elements.toast.classList.remove("show");
    }, 3200);
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function extractUrls(text) {
    const matches = String(text).match(/https?:\/\/[^\s]+/g) || [];
    const urls = [];

    for (const item of matches) {
        const clean = item.replace(/[).,;\]]+$/, "");
        if (!urls.includes(clean)) urls.push(clean);
    }

    return urls.slice(0, 5);
}

function siteName(url) {
    try {
        const hostname = new URL(url).hostname.replace(/^www\./, "");
        const first = hostname.split(".")[0].replaceAll("-", " ");
        return first.replace(/\b\w/g, (character) => character.toUpperCase()) || "Source";
    } catch {
        return "Source";
    }
}

function parseReaderItems(text) {
    const source = String(text).replace(/\r/g, "");
    const items = [];

    const standardPattern = /(\d+)\.\s*URL:\s*(https?:\/\/[^\s]+)\s*\n([\s\S]*?)(?=\n\s*\d+\.\s*URL:|$)/g;
    let match;

    while ((match = standardPattern.exec(source)) !== null) {
        items.push({
            number: match[1],
            url: match[2].replace(/[).,;\]]+$/, ""),
            summary: match[3].trim(),
        });
    }

    if (items.length) return items.slice(0, 5);

    // Compatibility fallback for older "Source N / URL / Summary" output.
    const fallbackPattern = /Source\s+(\d+)\s*\n\s*URL:\s*(https?:\/\/[^\s]+)\s*\n\s*(?:Summary:\s*)?([\s\S]*?)(?=\n\s*Source\s+\d+|$)/gi;

    while ((match = fallbackPattern.exec(source)) !== null) {
        items.push({
            number: match[1],
            url: match[2].replace(/[).,;\]]+$/, ""),
            summary: match[3].trim(),
        });
    }

    return items.slice(0, 5);
}

function renderSearch(text) {
    const urls = extractUrls(text);
    elements.searchSubtitle.textContent = `Found ${urls.length} relevant source${urls.length === 1 ? "" : "s"} from across the web`;

    if (!urls.length) {
        elements.searchResults.className = "agent-content empty-state";
        elements.searchResults.textContent = text || "No relevant URLs were found.";
        return;
    }

    elements.searchResults.className = "agent-content";
    elements.searchResults.innerHTML = urls.map((url, index) => `
        <div class="source-item">
            <div class="source-row">
                <div class="source-number">${index + 1}</div>
                <div class="source-meta">
                    <div class="source-site">${escapeHtml(siteName(url))}</div>
                    <a class="source-url" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(url)}</a>
                </div>
            </div>
        </div>
    `).join("");
}

function renderReader(text) {
    const items = parseReaderItems(text);
    elements.readerSubtitle.textContent = `Read and summarized ${items.length} source${items.length === 1 ? "" : "s"}`;

    if (!items.length) {
        elements.readerResults.className = "agent-content empty-state";
        elements.readerResults.textContent = text || "No source summaries were returned.";
        return;
    }

    elements.readerResults.className = "agent-content";
    elements.readerResults.innerHTML = items.map((item) => `
        <div class="source-item">
            <div class="source-row">
                <div class="source-number">${escapeHtml(item.number)}</div>
                <div class="source-meta">
                    <div class="source-site">${escapeHtml(siteName(item.url))}</div>
                    <a class="source-url" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.url)}</a>
                    <div class="source-summary">${escapeHtml(item.summary).replaceAll("\n", "<br>")}</div>
                </div>
            </div>
        </div>
    `).join("");
}

function inlineMarkdown(text) {
    let value = escapeHtml(text);
    value = value.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    value = value.replace(/`(.+?)`/g, "<code>$1</code>");
    value = value.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    return value;
}

function renderMarkdown(markdown) {
    const lines = String(markdown).replace(/\r/g, "").split("\n");
    const output = [];
    let listType = null;

    const closeList = () => {
        if (listType) {
            output.push(`</${listType}>`);
            listType = null;
        }
    };

    for (const raw of lines) {
        let line = raw.trim();

        if (!line) {
            closeList();
            continue;
        }

        // Defensive UI cleanup in case a provider emits a separator anyway.
        if (/^[-_=*~:]{3,}$/.test(line)) {
            closeList();
            continue;
        }

        if (/^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$/.test(line)) {
            closeList();
            continue;
        }

        if ((line.match(/\|/g) || []).length >= 2) {
            line = line
                .replace(/^\||\|$/g, "")
                .split("|")
                .map((cell) => cell.trim())
                .filter(Boolean)
                .join("; ");
        }

        const heading = line.match(/^(#{1,3})\s+(.+)$/);
        if (heading) {
            closeList();
            const level = heading[1].length;
            output.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
            continue;
        }

        const unordered = line.match(/^[-*]\s+(.+)$/);
        if (unordered) {
            if (listType !== "ul") {
                closeList();
                listType = "ul";
                output.push("<ul>");
            }
            output.push(`<li>${inlineMarkdown(unordered[1])}</li>`);
            continue;
        }

        const ordered = line.match(/^\d+[.)]\s+(.+)$/);
        if (ordered) {
            if (listType !== "ol") {
                closeList();
                listType = "ol";
                output.push("<ol>");
            }
            output.push(`<li>${inlineMarkdown(ordered[1])}</li>`);
            continue;
        }

        closeList();
        output.push(`<p>${inlineMarkdown(line)}</p>`);
    }

    closeList();
    return output.join("");
}

function renderReport(text) {
    elements.report.classList.remove("empty-report");
    elements.report.innerHTML = renderMarkdown(text);
    elements.download.disabled = false;
}

function extractSection(text, startLabel, endLabel = null) {
    const source = String(text);
    const start = source.toLowerCase().indexOf(startLabel.toLowerCase());
    if (start < 0) return "";

    const after = source.slice(start + startLabel.length);
    if (!endLabel) return after.trim();

    const end = after.toLowerCase().indexOf(endLabel.toLowerCase());
    return (end >= 0 ? after.slice(0, end) : after).trim();
}

function bulletLines(section) {
    return section
        .split("\n")
        .map((line) => line.trim().replace(/^[-*]\s*/, ""))
        .filter(Boolean);
}

function renderList(element, items, fallback) {
    element.innerHTML = "";
    const data = items.length ? items : [fallback];

    for (const item of data) {
        const li = document.createElement("li");
        li.textContent = item;
        element.appendChild(li);
    }
}

function renderCritic(text) {
    const scoreMatch = String(text).match(/Score:\s*(\d+(?:\.\d+)?)\s*\/\s*10/i);
    elements.score.textContent = scoreMatch ? scoreMatch[1] : "-";

    const strengths = bulletLines(extractSection(text, "Strengths:", "Areas to Improve:"));
    const improvements = bulletLines(extractSection(text, "Areas to Improve:", "One line verdict:"));
    const verdict = extractSection(text, "One line verdict:") || "No verdict was returned.";

    renderList(elements.strengths, strengths, "No strengths were returned.");
    renderList(elements.improvements, improvements, "No improvement suggestions were returned.");
    elements.verdict.textContent = verdict;
}

async function apiPost(path, payload) {
    const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    let body;
    try {
        body = await response.json();
    } catch {
        body = { error: `Unexpected server response (${response.status}).` };
    }

    if (!response.ok) {
        throw new Error(body.error || body.detail || `Request failed with status ${response.status}.`);
    }

    return body;
}

function resetOutput() {
    state.search = "";
    state.reader = "";
    state.report = "";
    state.critic = "";
    resetPipeline();

    elements.searchResults.className = "agent-content empty-state";
    elements.searchResults.textContent = "Searching for five relevant sources...";

    elements.readerResults.className = "agent-content empty-state";
    elements.readerResults.textContent = "Waiting for Search Agent results...";

    elements.report.className = "report-content empty-report";
    elements.report.textContent = "Your generated report will appear here after the pipeline completes.";

    elements.download.disabled = true;
    elements.score.textContent = "-";
    renderList(elements.strengths, [], "Feedback will appear after the Critic Chain completes.");
    renderList(elements.improvements, [], "Improvement suggestions will appear here.");
    elements.verdict.textContent = "The final verdict will appear here after the report is reviewed.";
    elements.scroll.hidden = true;
}

async function runPipeline() {
    const topic = elements.topic.value.trim();

    if (!topic) {
        showToast("Please enter a research topic first.", true);
        elements.topic.focus();
        return;
    }

    state.topic = topic;
    resetOutput();
    elements.run.disabled = true;
    setStatus("Research pipeline started", "Finding five relevant sources for your question.");

    try {
        setPipelineStep("search", "running");
        const searchData = await apiPost("/api/search", { topic });
        state.search = searchData.result;
        renderSearch(state.search);
        setPipelineStep("search", "done");

        setPipelineStep("reader", "running");
        setStatus("Reading selected sources", "Extracting the most important information from all five websites.");
        const readerData = await apiPost("/api/reader", {
            topic,
            search_results: state.search,
        });
        state.reader = readerData.result;
        renderReader(state.reader);
        setPipelineStep("reader", "done");
        elements.scroll.hidden = false;

        setPipelineStep("writer", "running");
        setStatus("Writing research report", "Combining source findings into a clear, structured answer.");
        const writerData = await apiPost("/api/writer", {
            topic,
            search_results: state.search,
            reader_results: state.reader,
        });
        state.report = writerData.result;
        renderReport(state.report);
        setPipelineStep("writer", "done");

        setPipelineStep("critic", "running");
        setStatus("Reviewing report", "Critic Chain is checking quality, completeness, and clarity.");
        const criticData = await apiPost("/api/critic", { report: state.report });
        state.critic = criticData.result;
        renderCritic(state.critic);
        setPipelineStep("critic", "done");

        setStatus("Research pipeline completed", "Search, Reader, Writer, and Critic stages completed successfully.");
        showToast("Research report generated successfully.");
    } catch (error) {
        setStatus("Research pipeline stopped", error.message);
        showToast(error.message, true);
    } finally {
        elements.run.disabled = false;
    }
}

elements.run.addEventListener("click", runPipeline);

elements.topic.addEventListener("keydown", (event) => {
    if (event.key === "Enter") runPipeline();
});

elements.scroll.addEventListener("click", () => {
    document.getElementById("report-screen").scrollIntoView({ behavior: "smooth" });
});

elements.download.addEventListener("click", () => {
    if (!state.report) return;

    const blob = new Blob([state.report], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `research_report_${Date.now()}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
});
