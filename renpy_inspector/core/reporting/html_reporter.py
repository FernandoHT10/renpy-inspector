"""Interactive, standalone single-file HTML report exporter for Ren'Py Inspector."""

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence, Union

from renpy_inspector.core.models.analysis import AnalysisResult, AnalysisStatus
from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.project import RenPyProject

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ren'Py Inspector QA Report — __PROJECT_NAME__</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --critical: #ef4444;
      --error: #f87171;
      --warning: #fbbf24;
      --info: #60a5fa;
      --success: #34d399;
      --code-bg: #090d16;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 2rem;
    }
    .container { max-width: 1200px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--border);
      margin-bottom: 2rem;
    }
    .brand { display: flex; align-items: center; gap: 0.75rem; }
    .logo {
      width: 40px; height: 40px;
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
      font-weight: bold; font-size: 1.25rem; color: #fff;
    }
    h1 { font-size: 1.5rem; font-weight: 700; }
    .meta { font-size: 0.875rem; color: var(--text-muted); }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
      text-align: center;
      cursor: pointer;
      transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .stat-card:hover { transform: translateY(-2px); border-color: var(--primary); }
    .stat-val { font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem; }
    .stat-label {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }
    .stat-card.critical .stat-val { color: var(--critical); }
    .stat-card.error .stat-val { color: var(--error); }
    .stat-card.warning .stat-val { color: var(--warning); }
    .stat-card.info .stat-val { color: var(--info); }
    .stat-card.total .stat-val { color: var(--primary); }

    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      margin-bottom: 1.5rem;
      background: var(--card-bg);
      padding: 1rem;
      border-radius: 8px;
      border: 1px solid var(--border);
      align-items: center;
    }
    .search-input {
      flex: 1;
      min-width: 250px;
      padding: 0.6rem 1rem;
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 6px;
      font-size: 0.9rem;
    }
    .filter-group { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .pill {
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 0.4rem 0.8rem;
      border-radius: 9999px;
      font-size: 0.8rem;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .pill.active {
      background: var(--primary);
      color: #0f172a;
      font-weight: 600;
      border-color: var(--primary);
    }

    .issues-list { display: flex; flex-direction: column; gap: 1rem; }
    .issue-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
      border-left: 4px solid var(--border);
      transition: border-color 0.15s ease;
    }
    .issue-card.CRITICAL { border-left-color: var(--critical); }
    .issue-card.ERROR { border-left-color: var(--error); }
    .issue-card.WARNING { border-left-color: var(--warning); }
    .issue-card.INFO { border-left-color: var(--info); }

    .issue-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.75rem;
    }
    .issue-badges { display: flex; gap: 0.5rem; align-items: center; }
    .badge {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .badge.CRITICAL { background: rgba(239, 68, 68, 0.2); color: var(--critical); }
    .badge.ERROR { background: rgba(248, 113, 113, 0.2); color: var(--error); }
    .badge.WARNING { background: rgba(251, 191, 36, 0.2); color: var(--warning); }
    .badge.INFO { background: rgba(96, 165, 250, 0.2); color: var(--info); }
    .badge.category { background: var(--border); color: var(--text-muted); }
    .issue-loc {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85rem;
      color: var(--primary);
    }
    .issue-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; }
    .issue-message { font-size: 0.95rem; color: #cbd5e1; margin-bottom: 0.75rem; }
    .snippet-box {
      background: var(--code-bg);
      padding: 0.6rem 0.8rem;
      border-radius: 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85rem;
      color: #e2e8f0;
      border: 1px solid rgba(255,255,255,0.05);
      margin-bottom: 0.75rem;
      overflow-x: auto;
    }
    .suggestion-box {
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid rgba(56, 189, 248, 0.25);
      border-radius: 6px;
      padding: 0.6rem 0.8rem;
      font-size: 0.875rem;
      color: #bae6fd;
      display: flex; gap: 0.5rem; align-items: baseline;
    }
    .empty-state {
      text-align: center;
      padding: 4rem 2rem;
      color: var(--text-muted);
      background: var(--card-bg);
      border-radius: 8px;
      border: 1px solid var(--border);
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="logo">RI</div>
        <div>
          <h1>Ren'Py Inspector QA Report</h1>
          <div class="meta">
            Project: <strong>__PROJECT_NAME__</strong> &bull; Generated: __GENERATED_AT__
          </div>
        </div>
      </div>
      <div class="meta" style="text-align: right;">
        <div>Duration: <strong>__DURATION__s</strong></div>
        <div>Path: <code>__PROJECT_PATH__</code></div>
      </div>
    </header>

    <div class="stats-grid">
      <div class="stat-card total" onclick="filterSeverity('ALL')">
        <div class="stat-val" id="count-total">__TOTAL_ISSUES__</div>
        <div class="stat-label">Total Issues</div>
      </div>
      <div class="stat-card critical" onclick="filterSeverity('CRITICAL')">
        <div class="stat-val" id="count-critical">__CRITICAL_ISSUES__</div>
        <div class="stat-label">Critical</div>
      </div>
      <div class="stat-card error" onclick="filterSeverity('ERROR')">
        <div class="stat-val" id="count-error">__ERROR_ISSUES__</div>
        <div class="stat-label">Errors</div>
      </div>
      <div class="stat-card warning" onclick="filterSeverity('WARNING')">
        <div class="stat-val" id="count-warning">__WARNING_ISSUES__</div>
        <div class="stat-label">Warnings</div>
      </div>
      <div class="stat-card info" onclick="filterSeverity('INFO')">
        <div class="stat-val" id="count-info">__INFO_ISSUES__</div>
        <div class="stat-label">Info</div>
      </div>
    </div>

    <div class="controls">
      <input type="text" id="search-input" class="search-input"
             placeholder="Search issues by keyword, file, or rule ID..."
             oninput="applyFilters()">
      <div class="filter-group" id="severity-pills">
        <button class="pill active" data-sev="ALL"
                onclick="setSeverityFilter('ALL')">All Severities</button>
        <button class="pill" data-sev="CRITICAL"
                onclick="setSeverityFilter('CRITICAL')">Critical</button>
        <button class="pill" data-sev="ERROR"
                onclick="setSeverityFilter('ERROR')">Error</button>
        <button class="pill" data-sev="WARNING"
                onclick="setSeverityFilter('WARNING')">Warning</button>
        <button class="pill" data-sev="INFO"
                onclick="setSeverityFilter('INFO')">Info</button>
      </div>
    </div>

    <div class="issues-list" id="issues-container">
      __ISSUES_HTML__
    </div>

    <div class="empty-state" id="empty-state" style="display: none;">
      <h2>No matching issues found</h2>
      <p>Try adjusting your search query or severity filters.</p>
    </div>
  </div>

  <script>
    let activeSeverity = 'ALL';

    function setSeverityFilter(sev) {
      activeSeverity = sev;
      document.querySelectorAll('#severity-pills .pill').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-sev') === sev);
      });
      applyFilters();
    }

    function filterSeverity(sev) {
      setSeverityFilter(sev);
    }

    function applyFilters() {
      const query = document.getElementById('search-input').value.toLowerCase().trim();
      const cards = document.querySelectorAll('.issue-card');
      let visibleCount = 0;

      cards.forEach(card => {
        const cardSev = card.getAttribute('data-severity');
        const textContent = card.innerText.toLowerCase();

        const matchesSev = (activeSeverity === 'ALL' || cardSev === activeSeverity);
        const matchesQuery = (!query || textContent.includes(query));

        if (matchesSev && matchesQuery) {
          card.style.display = 'block';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });

      document.getElementById('empty-state').style.display = visibleCount === 0 ? 'block' : 'none';
    }
  </script>
</body>
</html>
"""


class HtmlReporter:
    """Generates standalone, responsive single-file HTML reports."""

    @classmethod
    def generate_html(
        cls,
        project: Optional[RenPyProject] = None,
        issues: Optional[Sequence[Issue]] = None,
        scan_duration_seconds: float = 0.0,
        *,
        analysis_result: Optional[AnalysisResult] = None,
    ) -> str:
        """Render complete self-contained HTML report string."""
        if analysis_result is not None:
            eff_project = analysis_result.project or project
            eff_issues = analysis_result.issues
            eff_duration = analysis_result.scan_duration_seconds
        else:
            eff_project = project
            eff_issues = tuple(issues or ())
            eff_duration = scan_duration_seconds

        proj_name = eff_project.name if eff_project else "Unknown Project"
        proj_path = str(eff_project.root_path) if eff_project else ""

        critical_c = sum(1 for i in eff_issues if i.severity == Severity.CRITICAL)
        error_c = sum(1 for i in eff_issues if i.severity == Severity.ERROR)
        warning_c = sum(1 for i in eff_issues if i.severity == Severity.WARNING)
        info_c = sum(1 for i in eff_issues if i.severity == Severity.INFO)

        issue_items = []
        for it in eff_issues:
            loc = it.location
            loc_str = str(loc)
            sev = html.escape(it.severity.value)
            cat = html.escape(it.category.value)
            rid = html.escape(it.rule_id)

            snippet_html = ""
            if loc.source_snippet:
                snippet_html = f'<div class="snippet-box">{html.escape(loc.source_snippet)}</div>'

            card = f"""
            <div class="issue-card {sev}" data-severity="{sev}">
              <div class="issue-header">
                <div class="issue-badges">
                  <span class="badge {sev}">{sev}</span>
                  <span class="badge category">{cat}</span>
                  <span class="badge category">{rid}</span>
                </div>
                <div class="issue-loc">{html.escape(loc_str)}</div>
              </div>
              <div class="issue-title">{html.escape(it.title)}</div>
              <div class="issue-message">{html.escape(it.message)}</div>
              {snippet_html}
              <div class="suggestion-box">
                <strong>Fix:</strong> {html.escape(it.suggestion)}
              </div>
            </div>
            """
            issue_items.append(card)

        banner_html = ""
        diag_html = ""
        if analysis_result is not None:
            if analysis_result.status != AnalysisStatus.COMPLETE:
                st_val = html.escape(analysis_result.status.value)
                banner_html = f"""
                <div style="background: #451a03; border: 1px solid #f59e0b; color: #fef3c7;
                            padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;">
                  <h3 style="color: #fbbf24; margin-bottom: 0.5rem;">
                    ⚠️ Warning: Analysis Status is {st_val}
                  </h3>
                  <p>
                    Inspection could not cover 100% of the project.
                    Undetected issues may exist in unanalyzed files or unexecuted rules.
                  </p>
                </div>
                """

            if analysis_result.diagnostics:
                diags_rendered = "".join(
                    f"<li><strong>[{d.level.value} - {d.source.upper()}]</strong> "
                    f"{html.escape(d.message)}</li>"
                    for d in analysis_result.diagnostics
                )
                diag_html = f"""
                <details style="margin-top: 2rem; padding: 1rem; background: #1e293b;
                                border: 1px solid #334155; border-radius: 8px;">
                  <summary style="cursor: pointer; font-weight: bold; color: #38bdf8;">
                    Inspection Diagnostics ({len(analysis_result.diagnostics)})
                  </summary>
                  <ul style="margin-top: 0.75rem; padding-left: 1.5rem;
                             color: #cbd5e1; line-height: 1.7;">
                    {diags_rendered}
                  </ul>
                </details>
                """

        if issue_items:
            issues_html = banner_html + "\n".join(issue_items) + diag_html
        else:
            if analysis_result is not None and analysis_result.status != AnalysisStatus.COMPLETE:
                st_val = html.escape(analysis_result.status.value)
                issues_html = f"""
                {banner_html}
                <div class="empty-state"><h2>0 issues detected ({st_val})</h2>
                <p>Zero issues were detected by executed rules, but the inspection status is
                <strong>{st_val}</strong>. Uninspected code or failed rules may harbor
                undetected defects.</p>
                </div>
                {diag_html}
                """
            else:
                issues_html = (
                    '<div class="empty-state"><h2>No issues found</h2>'
                    '<p>Great job! The project passed inspection without any detected problems.</p>'
                    '</div>'
                    + diag_html
                )

        gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        content = HTML_TEMPLATE
        content = content.replace("__PROJECT_NAME__", html.escape(proj_name))
        content = content.replace("__PROJECT_PATH__", html.escape(proj_path))
        content = content.replace("__GENERATED_AT__", gen_time)
        content = content.replace("__DURATION__", f"{eff_duration:.2f}")
        content = content.replace("__TOTAL_ISSUES__", str(len(eff_issues)))
        content = content.replace("__CRITICAL_ISSUES__", str(critical_c))
        content = content.replace("__ERROR_ISSUES__", str(error_c))
        content = content.replace("__WARNING_ISSUES__", str(warning_c))
        content = content.replace("__INFO_ISSUES__", str(info_c))
        content = content.replace("__ISSUES_HTML__", issues_html)

        return content

    @classmethod
    def export(
        cls,
        output_path: Union[str, Path],
        project: Optional[RenPyProject] = None,
        issues: Optional[Sequence[Issue]] = None,
        scan_duration_seconds: float = 0.0,
        *,
        analysis_result: Optional[AnalysisResult] = None,
    ) -> Path:
        """Write the HTML report to disk."""
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        html_content = cls.generate_html(
            project=project,
            issues=issues,
            scan_duration_seconds=scan_duration_seconds,
            analysis_result=analysis_result,
        )

        with open(target, "w", encoding="utf-8") as f:
            f.write(html_content)

        return target
