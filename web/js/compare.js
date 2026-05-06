/**
 * compare.js — V6OP 报告对比
 * 依赖：common.js
 */
'use strict';

(function () {
  const { V6API, v6Esc, v6Alert, v6FmtDate } = V6Common;

  let _loadedReports = {};  // run_id -> report object

  document.addEventListener('DOMContentLoaded', function () {
    V6Common.V6Nav.init('compare');
    _bindControls();
    _loadRunList();

    // 从 URL 参数预填 run_id
    const params = new URLSearchParams(location.search);
    const preIds = (params.get('runs') || '').split(',').filter(Boolean);
    if (preIds.length) {
      preIds.forEach(function (id, i) {
        const sel = document.getElementById('cmp-sel-' + (i + 1));
        if (sel) {
          // 等待列表加载后选中
          setTimeout(function () {
            sel.value = id;
          }, 800);
        }
      });
      setTimeout(_doCompare, 1200);
    }
  });

  function _bindControls() {
    document.getElementById('btn-cmp-run')?.addEventListener('click', _doCompare);
    document.getElementById('btn-cmp-copy')?.addEventListener('click', _copyResult);
  }

  // ── 加载运行列表，填充 select ──────────────────────────────────────
  async function _loadRunList() {
    try {
      const r = await fetch(V6API.runs, { cache: 'no-store' });
      const d = await r.json();
      const runs = d.runs || [];
      // 填入所有 select
      [1, 2, 3, 4].forEach(function (i) {
        const sel = document.getElementById('cmp-sel-' + i);
        if (!sel) return;
        sel.innerHTML = '<option value="">（不选）</option>' +
          runs.map(function (run) {
            const label = (run.run_id || '').slice(0, 12) + ' | '
              + v6FmtDate(run.started_at || '') + ' | 命中'
              + (run.final_hit_count ?? '?');
            return `<option value="${v6Esc(run.run_id)}">${v6Esc(label)}</option>`;
          }).join('');
      });
    } catch (e) {
      v6Alert('cmp-alerts', 'warn', '加载列表失败：' + e.message);
    }
  }

  // ── 执行对比 ──────────────────────────────────────────────────────
  async function _doCompare() {
    const selectedIds = [1, 2, 3, 4]
      .map(function (i) { return document.getElementById('cmp-sel-' + i)?.value || ''; })
      .filter(Boolean);

    if (selectedIds.length < 2) {
      v6Alert('cmp-alerts', 'warn', '请至少选择 2 份报告');
      return;
    }

    const body    = document.getElementById('cmp-body');
    if (body) body.innerHTML = '<div class="text-muted">加载中…</div>';

    // 加载所有选中报告
    const reports = [];
    for (const runId of selectedIds) {
      if (_loadedReports[runId]) {
        reports.push(_loadedReports[runId]);
        continue;
      }
      try {
        const url = V6API.runs.replace(/\/?$/, '/') + runId;
        const r   = await fetch(url, { cache: 'no-store' });
        const d   = await r.json();
        d._run_id = runId;
        _loadedReports[runId] = d;
        reports.push(d);
      } catch {
        // 降级：用 run_report.json
        reports.push({ _run_id: runId, _error: '加载失败' });
      }
    }

    if (body) body.innerHTML = _renderCompare(reports);
  }

  function _renderCompare(reports) {
    // 命中集合
    const hitSets = reports.map(function (r) {
      return new Set(r.final_hit_codes || r.hit_codes || []);
    });

    // 共同命中
    let common = new Set(hitSets[0]);
    hitSets.slice(1).forEach(function (s) {
      for (const code of common) {
        if (!s.has(code)) common.delete(code);
      }
    });

    // 各自唯一命中
    const unique = hitSets.map(function (s, i) {
      const u = new Set(s);
      hitSets.forEach(function (other, j) {
        if (i !== j) for (const code of u) if (other.has(code)) u.delete(code);
      });
      return u;
    });

    // 表头
    const cols = reports.map(function (r, i) {
      const id      = r._run_id || ('报告' + (i + 1));
      const src     = r.strategy?.source?.type || '—';
      const hits    = (r.final_hit_codes || r.hit_codes || []).length;
      const path    = r.strategy?.path_type || r.path_type || '—';
      return `<th class="cmp-col-header">
        <div class="cmp-run-id">${v6Esc(id.slice(0, 16))}</div>
        <div class="cmp-run-meta">${v6Esc(src)} | ${v6Esc(path)}</div>
        <div class="cmp-run-hits">命中 ${hits} 只</div>
      </th>`;
    }).join('');

    // 行：共同命中
    const commonRow = `<tr>
      <td class="cmp-label">共同命中（${common.size} 只）</td>
      ${reports.map(function () {
        return `<td class="text-green" style="word-break:break-all">${v6Esc([...common].join(', ')) || '—'}</td>`;
      }).join('')}
    </tr>`;

    // 行：各自唯一
    const uniqueRows = reports.map(function (r, i) {
      const id = r._run_id || ('报告' + (i + 1));
      return `<tr>
        <td class="cmp-label">仅 ${v6Esc(id.slice(0, 10))} 命中（${unique[i].size} 只）</td>
        ${reports.map(function (_, j) {
          if (j === i) return `<td style="word-break:break-all">${v6Esc([...unique[i]].join(', ')) || '—'}</td>`;
          return `<td class="text-muted">—</td>`;
        }).join('')}
      </tr>`;
    }).join('');

    // 参数对比行
    const fields = [
      ['来源类型',  function (r) { return r.strategy?.source?.type || r.source_type || '—'; }],
      ['Query',     function (r) { const q = r.strategy?.source?.query || r.query_text || '—'; return q.length > 60 ? q.slice(0, 60) + '…' : q; }],
      ['技能链路',  function (r) { return (r.strategy?.skills || r.skills || []).join('+') || '—'; }],
      ['执行路径',  function (r) { return r.strategy?.path_type || r.path_type || '—'; }],
      ['命中总数',  function (r) { return String(r.final_hit_count ?? (r.final_hit_codes || []).length); }],
      ['失败数',    function (r) { return String((r.failed_codes || []).length); }],
    ];

    const paramRows = fields.map(function (pair) {
      const label = pair[0];
      const fn    = pair[1];
      const vals  = reports.map(fn);
      const allSame = vals.every(function (v) { return v === vals[0]; });
      return `<tr>
        <td class="cmp-label">${v6Esc(label)}</td>
        ${vals.map(function (v) {
          return `<td class="${allSame ? '' : 'cmp-diff'}" style="font-size:11px;word-break:break-all">${v6Esc(v)}</td>`;
        }).join('')}
      </tr>`;
    }).join('');

    return `<table class="cmp-table">
      <thead><tr><th class="cmp-label">对比项</th>${cols}</tr></thead>
      <tbody>
        ${commonRow}
        ${uniqueRows}
        <tr><td colspan="${reports.length + 1}" style="padding:6px 8px;color:var(--muted);font-size:11px;font-weight:600">── 参数差异 ──</td></tr>
        ${paramRows}
      </tbody>
    </table>`;
  }

  // ── 复制对比结果 ──────────────────────────────────────────────────
  function _copyResult() {
    const body = document.getElementById('cmp-body');
    if (!body) return;
    const text = body.innerText || body.textContent || '';
    navigator.clipboard?.writeText(text).then(function () {
      v6Alert('cmp-alerts', 'ok', '已复制对比文本');
    }).catch(function () {
      v6Alert('cmp-alerts', 'warn', '复制失败，请手动选择复制');
    });
  }

})();
