
function renderThreatGraph(id, items, field, source = false) {
    const chart = document.getElementById(id);
    chart.replaceChildren();

    const maximum = Math.max(1, ...items.map(item => item.total));

    for (const item of items) {
        const row = document.createElement("div");
        row.className = "threat-row";

        const label = document.createElement("span");
        label.className = "threat-label";
        label.textContent = item[field];

        const track = document.createElement("div");
        track.className = "chart-track";

        const bar = document.createElement("div");
        bar.className = source
            ? "threat-bar source-bar"
            : "threat-bar";

        bar.style.width = `${item.total / maximum * 100}%`;

        const value = document.createElement("span");
        value.textContent = item.total;

        track.appendChild(bar);
        row.append(label, track, value);
        chart.appendChild(row);
    }
}

let dashboardData = null;
let updatingStatus = false;
let refreshing = false;

function renderChart(counts) {
    const chart = document.getElementById("severity-chart");
    chart.replaceChildren();

    const levels = [
        "Critical", "High", "Medium", "Low", "Unknown"
    ];

    const maximum = Math.max(1, ...Object.values(counts));

    for (const level of levels) {
        const count = counts[level] || 0;

        const row = document.createElement("div");
        row.className = "chart-row";

        const label = document.createElement("span");
        label.textContent = level;

        const track = document.createElement("div");
        track.className = "chart-track";

        const bar = document.createElement("div");
        bar.className = "chart-bar " + level.toLowerCase();
        bar.style.width = `${count / maximum * 100}%`;

        const value = document.createElement("span");
        value.textContent = count;

        track.appendChild(bar);
        row.append(label, track, value);
        chart.appendChild(row);
    }
}

async function updateStatus(id, status) {
    updatingStatus = true;

    try {
        const response = await fetch(
            `/api/alerts/${id}/status`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ status })
            }
        );

        if (!response.ok) {
            throw new Error("Status update failed");
        }

    } catch (error) {
        alert("Unable to update incident status.");
        console.error(error);

    } finally {
        updatingStatus = false;
        await refreshDashboard();
    }
}

function renderAlerts() {
    if (!dashboardData) return;


    const alerts = dashboardData.alerts;

    const tbody = document.getElementById("alerts");
    tbody.replaceChildren();

    const fields = [
        "id",
        "event_timestamp",
        "source_ip",
        "destination_ip",
        "signature",
        "original_severity",
        "severity",
        "related_alerts",
        "priority",
        "recommended_response",
        "status"
    ];

    for (const item of alerts) {
        const row = document.createElement("tr");

        for (const field of fields) {
            const cell = document.createElement("td");

            
if (field === "id" || field === "signature") {
                const link = document.createElement("button");

                link.type = "button";
                link.className = "alert-link";

                link.textContent = field === "id"
                    ? "#" + item.id
                    : item.signature || "Unknown Alert";

                link.addEventListener("click", () => {
                    openInvestigation(item.id);
                });

                cell.appendChild(link);

            } else if (field === "status") {
                const select = document.createElement("select");

                select.className =
                    "status-select status-" +
                    item.status.toLowerCase();

                for (const status of [
                    "Open", "Investigating", "Resolved"
                ]) {
                    const option = document.createElement("option");
                    option.value = status;
                    option.textContent = status;
                    select.appendChild(option);
                }

                select.value = item.status;

                select.addEventListener("change", () => {
                    updateStatus(item.id, select.value);
                });

                cell.appendChild(select);

            } else {
                cell.textContent = item[field] ?? "N/A";

                if (field === "severity") {
                    cell.className = String(
                        item.severity || "unknown"
                    ).toLowerCase();
                }
            }

            row.appendChild(cell);
        }

        tbody.appendChild(row);
    }
}

async function refreshDashboard() {
    if (updatingStatus || refreshing) return;

    refreshing = true;

    try {
        const response = await fetch("/api/alerts", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("API request failed");
        }

        dashboardData = await response.json();

        document.getElementById("total").textContent =
            dashboardData.total;

        for (const level of [
            "Critical", "High", "Medium", "Low"
        ]) {
            document.getElementById(
                level.toLowerCase()
            ).textContent = dashboardData.counts[level] || 0;
        }

        document.getElementById("open").textContent =
            dashboardData.open_alerts;

        
        renderSOCAnalytics(dashboardData);

        if (!document.activeElement.matches(".status-select")) {
            await loadAlertPage();
        }

        document.getElementById("connection").textContent =
            "Database connected | Updated: " +
            new Date().toLocaleTimeString();

    } catch (error) {
        document.getElementById("connection").textContent =
            "Dashboard connection error";

        console.error(error);

    } finally {
        refreshing = false;
    }
}



let currentPage = 1;
let pageSize = 30;
let totalPages = 1;
let pageRequest = 0;
let searchTimer;

async function loadAlertPage() {
    const requestId = ++pageRequest;

    const params = new URLSearchParams({
        page: currentPage,
        limit: pageSize,
        search: document.getElementById("search").value,
        severity: document.getElementById("severity-filter").value,
        status: document.getElementById("status-filter").value
    });

    try {
        const response = await fetch(
            "/api/alerts/page?" + params.toString(),
            { cache: "no-store" }
        );

        if (!response.ok) {
            throw new Error("Pagination request failed");
        }

        const data = await response.json();

        if (requestId !== pageRequest) return;

        currentPage = data.page;
        totalPages = data.pages;

        dashboardData = dashboardData || {};
        dashboardData.alerts = data.alerts;

        const first = data.total
            ? (currentPage - 1) * pageSize + 1
            : 0;

        const last = Math.min(
            currentPage * pageSize,
            data.total
        );

        document.getElementById("pagination-info").textContent =
            `Showing ${first}-${last} of ${data.total} alerts`;

        document.getElementById("page-indicator").textContent =
            `Page ${currentPage} of ${totalPages}`;

        document.getElementById("result-count").textContent =
            `${data.total} matching alerts`;

        document.getElementById("previous-page").disabled =
            currentPage <= 1;

        document.getElementById("next-page").disabled =
            currentPage >= totalPages;

        if (!document.activeElement.matches(".status-select")) {
            renderAlerts();
        }

    } catch (error) {
        document.getElementById("pagination-info").textContent =
            "Unable to load alerts";

        console.error(error);
    }
}

function resetPagination() {
    currentPage = 1;
    loadAlertPage();
}

document.getElementById("previous-page")
    .addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            loadAlertPage();
        }
    });

document.getElementById("next-page")
    .addEventListener("click", () => {
        if (currentPage < totalPages) {
            currentPage++;
            loadAlertPage();
        }
    });

document.getElementById("page-size")
    .addEventListener("change", event => {
        pageSize = Number(event.target.value);
        resetPagination();
    });

document.getElementById("search")
    .addEventListener("input", () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(resetPagination, 250);
    });

document.getElementById("severity-filter")
    .addEventListener("change", resetPagination);

document.getElementById("status-filter")
    .addEventListener("change", resetPagination);


refreshDashboard();
setInterval(refreshDashboard, 5000);

function renderPieChart(id, items) {
    const container = document.getElementById(id);
    container.replaceChildren();

    const total = items.reduce(
        (sum, item) => sum + item.total, 0
    );

    if (!total) {
        container.textContent = "No alerts available";
        return;
    }

    const pie = document.createElement("div");
    pie.className = "pie-chart";

    const legend = document.createElement("div");
    legend.className = "pie-legend";

    let position = 0;
    const segments = [];

    for (const item of items) {
        if (!item.total) continue;

        const percent = item.total / total * 100;
        const end = position + percent;

        segments.push(
            `${item.color} ${position}% ${end}%`
        );

        const entry = document.createElement("div");
        entry.className = "pie-legend-entry";

        const dot = document.createElement("span");
        dot.className = "pie-dot";
        dot.style.background = item.color;

        const label = document.createElement("span");
        label.textContent =
            `${item.label}: ${item.total} (${percent.toFixed(1)}%)`;

        entry.append(dot, label);
        legend.appendChild(entry);

        position = end;
    }

    pie.style.background =
        `conic-gradient(${segments.join(",")})`;

    container.append(pie, legend);
}

function renderDonutChart(id, items) {
    const container = document.getElementById(id);
    container.replaceChildren();

    const total = items.reduce(
        (sum, item) => sum + Number(item.total), 0
    );

    const donut = document.createElement("div");
    donut.className = "soc-donut";

    const center = document.createElement("div");
    center.className = "soc-donut-center";

    const number = document.createElement("span");
    number.className = "soc-donut-total";
    number.textContent = total;

    const caption = document.createElement("span");
    caption.className = "soc-donut-caption";
    caption.textContent = "Alerts";

    center.append(number, caption);
    donut.appendChild(center);

    const legend = document.createElement("div");
    legend.className = "soc-legend";

    let position = 0;
    const segments = [];

    for (const item of items) {
        const count = Number(item.total);

        if (total > 0 && count > 0) {
            const end = position + count / total * 100;

            segments.push(
                `${item.color} ${position}% ${end}%`
            );

            position = end;
        }

        const row = document.createElement("div");
        row.className = "soc-legend-row";

        const dot = document.createElement("span");
        dot.className = "soc-legend-dot";
        dot.style.background = item.color;

        const label = document.createElement("span");
        label.className = "soc-legend-label";
        label.textContent = item.label;

        const value = document.createElement("span");
        value.className = "soc-legend-value";
        value.textContent = count;

        row.append(dot, label, value);
        legend.appendChild(row);
    }

    donut.style.background = segments.length
        ? `conic-gradient(${segments.join(",")})`
        : "#334155";

    container.append(donut, legend);
}

function renderProgressChart(id, items, denominator) {
    const container = document.getElementById(id);
    container.replaceChildren();

    const maximum = Math.max(1, denominator);

    for (const item of items) {
        const row = document.createElement("div");
        row.className = "soc-progress-row";

        const label = document.createElement("div");
        label.className = "soc-progress-label";
        label.textContent = `${item.label} — ${item.total}`;

        const track = document.createElement("div");
        track.className = "soc-progress-track";

        const fill = document.createElement("div");
        fill.className = "soc-progress-fill";
        fill.style.background = item.color;
        fill.style.width =
            `${Math.min(100, item.total / maximum * 100)}%`;

        track.appendChild(fill);
        row.append(label, track);
        container.appendChild(row);
    }
}

function renderSOCAnalytics(data) {
    const severityColors = {
        Critical: "#ef4444",
        High: "#f97316",
        Medium: "#eab308",
        Low: "#22c55e",
        Unknown: "#64748b"
    };

    const threatColors = [
        "#38bdf8",
        "#a78bfa",
        "#f97316",
        "#64748b",
        "#22c55e",
        "#ec4899",
        "#eab308"
    ];

    renderDonutChart(
        "severity-chart",
        Object.entries(data.counts).map(
            ([label, total]) => ({
                label,
                total,
                color: severityColors[label] || "#64748b"
            })
        )
    );

    renderDonutChart(
        "threat-chart",
        data.threat_categories.map((item, i) => ({
            label: item.category,
            total: item.total,
            color: threatColors[i] ||
                `hsl(${(i * 137.5) % 360}, 75%, 58%)`
        }))
    );

    const sources = data.top_sources.map(item => ({
        label: item.source_ip,
        total: item.total,
        color: "#38bdf8"
    }));

    renderProgressChart(
        "source-chart",
        sources,
        Math.max(1, ...sources.map(item => item.total))
    );

    const statusColors = {
        Open: "#f97316",
        Investigating: "#38bdf8",
        Resolved: "#22c55e"
    };

    renderProgressChart(
        "incident-chart",
        Object.entries(data.status_counts).map(
            ([label, total]) => ({
                label,
                total,
                color: statusColors[label] || "#64748b"
            })
        ),
        data.total
    );
}

function renderDonutChart(id, items) {
    const container = document.getElementById(id);
    container.replaceChildren();

    const total = items.reduce(
        (sum, item) => sum + Number(item.total), 0
    );

    const donut = document.createElement("div");
    donut.className = "soc-donut";

    const center = document.createElement("div");
    center.className = "soc-donut-center";

    const number = document.createElement("span");
    number.className = "soc-donut-total";
    number.textContent = total;

    const caption = document.createElement("span");
    caption.className = "soc-donut-caption";
    caption.textContent = "Alerts";

    center.append(number, caption);
    donut.appendChild(center);

    const legend = document.createElement("div");
    legend.className = "soc-legend";

    let position = 0;
    const segments = [];

    for (const item of items) {
        const count = Number(item.total);

        if (total > 0 && count > 0) {
            const end = position + count / total * 100;

            segments.push(
                `${item.color} ${position}% ${end}%`
            );

            position = end;
        }

        const row = document.createElement("div");
        row.className = "soc-legend-row";

        const dot = document.createElement("span");
        dot.className = "soc-legend-dot";
        dot.style.background = item.color;

        const label = document.createElement("span");
        label.className = "soc-legend-label";
        label.textContent = item.label;

        const value = document.createElement("span");
        value.className = "soc-legend-value";
        value.textContent = count;

        row.append(dot, label, value);
        legend.appendChild(row);
    }

    donut.style.background = segments.length
        ? `conic-gradient(${segments.join(",")})`
        : "#334155";

    container.append(donut, legend);
}

function renderProgressChart(id, items, denominator) {
    const container = document.getElementById(id);
    container.replaceChildren();

    const maximum = Math.max(1, denominator);

    for (const item of items) {
        const row = document.createElement("div");
        row.className = "soc-progress-row";

        const label = document.createElement("div");
        label.className = "soc-progress-label";
        label.textContent = `${item.label} — ${item.total}`;

        const track = document.createElement("div");
        track.className = "soc-progress-track";

        const fill = document.createElement("div");
        fill.className = "soc-progress-fill";
        fill.style.background = item.color;
        fill.style.width =
            `${Math.min(100, item.total / maximum * 100)}%`;

        track.appendChild(fill);
        row.append(label, track);
        container.appendChild(row);
    }
}

function renderSOCAnalytics(data) {
    const severityColors = {
        Critical: "#ef4444",
        High: "#f97316",
        Medium: "#eab308",
        Low: "#22c55e",
        Unknown: "#64748b"
    };

    const threatColors = [
        "#38bdf8",
        "#a78bfa",
        "#f97316",
        "#64748b",
        "#22c55e",
        "#ec4899",
        "#eab308"
    ];

    renderDonutChart(
        "severity-chart",
        Object.entries(data.counts).map(
            ([label, total]) => ({
                label,
                total,
                color: severityColors[label] || "#64748b"
            })
        )
    );

    renderDonutChart(
        "threat-chart",
        data.threat_categories.map((item, i) => ({
            label: item.category,
            total: item.total,
            color: threatColors[i] ||
                `hsl(${(i * 137.5) % 360}, 75%, 58%)`
        }))
    );

    const sources = data.top_sources.map(item => ({
        label: item.source_ip,
        total: item.total,
        color: "#38bdf8"
    }));

    renderProgressChart(
        "source-chart",
        sources,
        Math.max(1, ...sources.map(item => item.total))
    );

    const statusColors = {
        Open: "#f97316",
        Investigating: "#38bdf8",
        Resolved: "#22c55e"
    };

    renderProgressChart(
        "incident-chart",
        Object.entries(data.status_counts).map(
            ([label, total]) => ({
                label,
                total,
                color: statusColors[label] || "#64748b"
            })
        ),
        data.total
    );
}

/* Live Alert Timeline */

let timelineRequest = 0;

async function loadTimeline() {
    const requestId = ++timelineRequest;

    const range = document.getElementById(
        "timeline-range"
    ).value;

    try {
        const response = await fetch(
            `/api/alerts/timeline?range=${range}`,
            { cache: "no-store" }
        );

        if (!response.ok) {
            throw new Error("Timeline request failed");
        }

        const data = await response.json();

        if (requestId !== timelineRequest) return;

        renderTimeline(data);

    } catch (error) {
        if (requestId !== timelineRequest) return;

        document.getElementById(
            "timeline-summary"
        ).textContent = "Unable to load timeline";

        console.error(error);
    }
}

function renderTimeline(data) {
    const container = document.getElementById(
        "timeline-chart"
    );

    const points = data.timeline;

    document.getElementById(
        "timeline-summary"
    ).textContent =
        `${data.total} security alerts during selected period`;

    const width = 1000;
    const height = 260;
    const left = 45;
    const right = 25;
    const top = 20;
    const bottom = 40;

    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;

    const maximum = Math.max(
        5, ...points.map(p => p.total)
    );

    const yMax = Math.ceil(maximum / 5) * 5;

    const x = i =>
        left + i * plotWidth /
        Math.max(1, points.length - 1);

    const y = count =>
        top + plotHeight -
        count / yMax * plotHeight;

    const ns = "http://www.w3.org/2000/svg";

    function element(tag, attributes, content) {
        const node = document.createElementNS(ns, tag);

        for (const [key, value] of
            Object.entries(attributes)) {
            node.setAttribute(key, value);
        }

        if (content !== undefined) {
            node.textContent = content;
        }

        return node;
    }

    const svg = element("svg", {
        viewBox: `0 0 ${width} ${height}`,
        role: "img",
        "aria-label": "Security alert activity over time"
    });

    for (let i = 0; i <= 5; i++) {
        const value = i * yMax / 5;
        const position = y(value);

        svg.appendChild(element("line", {
            x1: left,
            x2: width - right,
            y1: position,
            y2: position,
            stroke: "#334155",
            "stroke-dasharray": "4 5"
        }));

        svg.appendChild(element("text", {
            x: left - 10,
            y: position + 4,
            fill: "#94a3b8",
            "font-size": 12,
            "text-anchor": "end"
        }, value));
    }

    const coords = points.map(
        (p, i) => `${x(i)},${y(p.total)}`
    );

    const baseline = y(0);

    const area = `
        M ${x(0)},${baseline}
        L ${coords.join(" L ")}
        L ${x(points.length - 1)},${baseline}
        Z
    `;

    svg.appendChild(element("path", {
        d: area,
        fill: "#38bdf8",
        opacity: 0.12
    }));

    svg.appendChild(element("polyline", {
        points: coords.join(" "),
        fill: "none",
        stroke: "#38bdf8",
        "stroke-width": 2.5,
        "stroke-linejoin": "round",
        "stroke-linecap": "round"
    }));

    points.forEach((point, i) => {
        const circle = element("circle", {
            cx: x(i),
            cy: y(point.total),
            r: 4,
            fill: "#38bdf8"
        });

        const date = new Date(
            point.timestamp * 1000
        );

        circle.appendChild(element("title", {},
            `${date.toLocaleString()}: ${point.total} alerts`
        ));

        svg.appendChild(circle);
    });

    for (let i = 0; i <= 4; i++) {
        const index = Math.round(
            i * (points.length - 1) / 4
        );

        const date = new Date(
            points[index].timestamp * 1000
        );

        const label =
            data.range === "1h" || data.range === "24h"
            ? date.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit"
            })
            : date.toLocaleDateString([], {
                month: "short",
                day: "numeric"
            });

        svg.appendChild(element("text", {
            x: x(index),
            y: height - 12,
            fill: "#94a3b8",
            "font-size": 12,
            "text-anchor": "middle"
        }, label));
    }

    container.replaceChildren(svg);
}

document.getElementById("timeline-range")
    .addEventListener("change", loadTimeline);

loadTimeline();
setInterval(loadTimeline, 5000);

/* Alert Investigation */

let activeInvestigation = null;
let investigationRequest = 0;

function investigationSection(title, fields, grid = true) {
    const section = document.createElement("section");
    section.className = "investigation-section";

    const heading = document.createElement("h3");
    heading.textContent = title;

    const content = document.createElement("div");

    if (grid) {
        content.className = "investigation-grid";
    }

    for (const [label, value, color] of fields) {
        const field = document.createElement("div");
        field.className = "investigation-field";

        const name = document.createElement("div");
        name.className = "investigation-label";
        name.textContent = label;

        const text = document.createElement("div");
        text.className = "investigation-value";
        text.textContent = value ?? "N/A";

        if (color) {
            text.style.color = color;
        }

        field.append(name, text);
        content.appendChild(field);
    }

    section.append(heading, content);
    return section;
}

async function openInvestigation(id) {
    const requestId = ++investigationRequest;

    const panel = document.getElementById(
        "investigation-panel"
    );

    const content = document.getElementById(
        "investigation-content"
    );

    const save = document.getElementById(
        "save-investigation"
    );

    activeInvestigation = null;
    save.disabled = true;

    document.getElementById(
        "investigation-id"
    ).textContent = `SECURITY ALERT #${id}`;

    document.getElementById(
        "investigation-title"
    ).textContent = "Loading alert...";

    document.getElementById(
        "investigation-message"
    ).textContent = "";

    content.replaceChildren();

    if (!panel.open) {
        panel.showModal();
    }

    try {
        const response = await fetch(
            `/api/alerts/${id}`,
            { cache: "no-store" }
        );

        if (!response.ok) {
            throw new Error("Unable to retrieve alert");
        }

        const alert = await response.json();

        if (requestId !== investigationRequest) return;

        activeInvestigation = alert.id;

        const colors = {
            Critical: "#ef4444",
            High: "#f97316",
            Medium: "#eab308",
            Low: "#22c55e",
            Unknown: "#94a3b8"
        };

        document.getElementById(
            "investigation-title"
        ).textContent = alert.signature || "Unknown Alert";

        content.append(
            investigationSection("Network Information", [
                ["Source IP", alert.source_ip],
                ["Destination IP", alert.destination_ip],
                ["Source Port", alert.source_port],
                ["Destination Port", alert.destination_port],
                ["Protocol", alert.protocol],
                ["Threat Category", alert.category]
            ]),

            investigationSection("Threat Analysis", [
                [
                    "Original Severity",
                    alert.original_severity,
                    colors[alert.original_severity]
                ],
                [
                    "Current Severity",
                    alert.severity,
                    colors[alert.severity]
                ],
                ["Related Alerts", alert.related_alerts],
                ["Priority", alert.priority]
            ]),

            investigationSection("Event Information", [
                ["Event Timestamp", alert.event_timestamp],
                ["Database Timestamp", alert.created_at]
            ]),

            investigationSection("Recommended Response", [
                ["Response Action", alert.recommended_response]
            ], false)
        );

        document.getElementById(
            "investigation-status"
        ).value = alert.status;

        save.disabled = false;

    } catch (error) {
        if (requestId !== investigationRequest) return;

        content.textContent = "Unable to load alert details.";
        console.error(error);
    }
}

async function saveInvestigationStatus() {
    if (activeInvestigation === null) return;

    const id = activeInvestigation;

    const status = document.getElementById(
        "investigation-status"
    ).value;

    const message = document.getElementById(
        "investigation-message"
    );

    const save = document.getElementById(
        "save-investigation"
    );

    save.disabled = true;
    message.textContent = "Saving status...";

    try {
        const response = await fetch(
            `/api/alerts/${id}/status`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ status })
            }
        );

        if (!response.ok) {
            throw new Error("Status update failed");
        }

        if (activeInvestigation === id) {
            message.textContent = "Status saved successfully.";
            message.style.color = "#22c55e";
        }

        await refreshDashboard();

    } catch (error) {
        if (activeInvestigation === id) {
            message.textContent = "Unable to save status.";
            message.style.color = "#ef4444";
        }

        console.error(error);

    } finally {
        if (activeInvestigation === id) {
            save.disabled = false;
        }
    }
}

document.getElementById("close-investigation")
    .addEventListener("click", () => {
        document.getElementById(
            "investigation-panel"
        ).close();
    });

document.getElementById("investigation-panel")
    .addEventListener("close", () => {
        activeInvestigation = null;
        investigationRequest++;
    });

document.getElementById("save-investigation")
    .addEventListener("click", saveInvestigationStatus);
