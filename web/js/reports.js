/**
 * reports.js — V6OP 报告中心
 * 依赖：common.js
 */
'use strict';

(function () {
  const { V6API, v6Esc, v6Alert, v6FmtDate, V6Store } = V6Common;

  let _allRuns    = [];
  let _searchQ    = '';
  let _srcFilter  = '';
  let _sortField  = 'run_id';
  let _sortDir    = -1;   // -1 = desc

  // ── 入口 ────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    V6Common.V6Nav.init('reports');
    _bindControls();
    _loadRuns();
  });

  function _bindControls() {
    document.getElementById('rpt-search')?.addEventListener('input', function () {
      _searchQ = this.value.toLowerCase().trim();
      _renderList();
    });
    document.getElementById('rpt-src-filter')?.addEventListener('change', function () {
      _srcFilter = this.value;
      _renderList();
    });
    document.querySelectorAll('[data-sort]').forEach(function (th) {
      th.addEventListener('click', function () {
        const field = th.dataset.sort;
        if (_sortField === field) _sortDir = -_sortDir;
        else { _sortField = field; _sortDir = -1; }
        _renderList();
      });
    });
    document.getElementById('btn-rpt-refresh')?.addEventListener('click', _loadRuns);
    document.getElementById('btn-rpt-compare')?.addEventListener('click', _goCompare);
  }

  // ── 加载运行列表 ──────────────────────────────────────────────────
  async function _loadRuns() {
    const container = document.getElementById('rpt-list-body');
    if (container) container.innerHTML = '<tr><td colspan="8" class="text-muted" style="padding:16px">加载中…</td></tr>';
    try {
      const r = await fetch(V6API.runs, { cache: 'no-store' });
      const d = await r.json();
      _allRuns = (d.runs || []).map(function (run) {
        // Normalize common fields
        return {
          run_id:      run.run_id || '—',
          started_at:  run.started_at || run.generated_at || '',
          source_type: run.strategy?.source?.type || run.source_type || '—',
          query_text:  run.strategy?.source?.query || run.query_text || '',
          hit_count:   run.final_hit_count ?? run.hit_count ?? '—',
          failed_count:run.failed_count ?? 0,
          skills:      (run.strategy?.skills || run.skills || []).join('+') || '—',
          path_type:   run.strategy?.path_type || run.path_type || '—',
          _raw:        run,
        };
      });
      _renderList();
    } catch (e) {
      if (container) container.innerHTML =
        `<tr><td colspan="8" class="text-muted">加载失败：${v6Esc(e.message)}</td></tr>`;
    }
  }

  // ── 过滤 + 排序 ───────────────────────────────────────────────────
  function _filtered() {
    return _allRuns.filter(function (r) {
      if (_srcFilter && r.source_type !== _srcFilter) return false;
      if (!_searchQ) return true;
      return r.run_id.toLowerCase().includes(_searchQ)
          || r.query_text.toLowerCase().includes(_searchQ)
          || r.skills.toLowerCase().includes(_searchQ);
    }).sort(function (a, b) {
      const av = a[_sortField] ?? '';
      const bv = b[_sortField] ?? '';
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * _sortDir;
      return String(av).localeCompare(String(bv)) * _sortDir;
    });
  }

  // ── 渲染列表 ──────────────────────────────────────────────────────
  function _renderList() {
    const tbody  = document.getElementById('rpt-list-body');
    const count  = document.getElementById('rpt-count');
    if (!tbody) return;
    const rows   = _filtered();
    if (count) count.textContent = rows.length + ' 条';

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-muted" style="padding:16px">无符合条件的报告</td></tr>';
      return;
    }

    tbody.innerHTML = rows.map(function (r, i) {
      const hitCls    = (r.hit_count > 0) ? 'text-green' : 'text-muted';
      const failedCls = (r.failed_count > 0) ? 'text-yellow' : '';
      const queryPreview = r.query_text.length > 40
        ? r.query_text.slice(0, 40) + '…' : r.query_text;
      return `<tr class="rpt-row" data-idx="${i}">
        <td><input type="checkbox" class="rpt-chk" data-idx="${i}" /></td>
        <td class="monospace" style="font-size:11px">${v6Esc(r.run_id)}</td>
        <td style="white-space:nowrap;font-size:11px">${v6Esc(v6FmtDate(r.started_at))}</td>
        <td><span class="tag">${v6Esc(r.source_type)}</span></td>
        <td title="${v6Esc(r.query_text)}" style="font-size:11px">${v6Esc(queryPreview)}</td>
        <td class="${hitCls}" style="text-align:right">${v6Esc(String(r.hit_count))}</td>
        <td class="${failedCls}" style="text-align:right">${r.failed_count || 0}</td>
        <td style="font-size:11px">${v6Esc(r.skills)}</td>
        <td style="font-size:11px">${v6Esc(r.path_type)}</td>
        <td>
          <button class="btn btn-sm" onclick="_rptOpen('${v6Esc(r.run_id)}')" type="button">详情</button>
          <button class="btn btn-sm" onclick="_rptLoad('${v6Esc(r.run_id)}')" type="button">载入策略</button>
        </td>
      </tr>`;
    }).join('');
  }

  // ── 查看详情 ──────────────────────────────────────────────────────
  window._rptOpen = async function (runId) {
    const panel = document.getElementById('rpt-detail-panel');
    const body  = document.getElementById('rpt-detail-body');
    if (!panel || !body) return;
    panel.classList.remove('hidden');
    body.innerHTML = '<div class="text-muted">加载中…</div>';

    try {
      // 从 /api/runs/{run_id} 获取详情（新 API），降级到 /api/result
      const url = V6API.runs.replace(/\/?$/, '/') + runId;
      const r   = await fetch(url, { cache: 'no-store' });
      const d   = await r.json();
      body.innerHTML = _renderDetail(d, runId);
    } catch (e) {
      body.innerHTML = `<span class="text-red">加载失败：${v6Esc(e.message)}</span>`;
    }
  };

  function _renderDetail(d, runId) {
    const strategy = d.strategy || d.strategy_snapshot || {};
    const src      = strategy.source || {};
    const skills   = (strategy.skills || d.skills || []).join(', ') || '—';
    const hits     = (d.final_hit_codes || d.hit_codes || []);
    const failed   = (d.failed_codes || []);

    return `<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        <h3 style="margin:0;font-size:14px">${v6Esc(runId)}</h3>
        <button class="btn btn-sm" onclick="document.getElementById('rpt-detail-panel').classList.add('hidden')">✕ 关闭</button>
      </div>
      <table class="rpt-detail-table">
        <tr><td>来源</td><td>${v6Esc(src.type || '—')}</td></tr>
        <tr><td>Query</td><td style="word-break:break-all">${v6Esc(src.query || '—')}</td></tr>
        <tr><td>Limit</td><td>${v6Esc(String(src.limit ?? '—'))}</td></tr>
        <tr><td>技能链路</td><td>${v6Esc(skills)}</td></tr>
        <tr><td>执行路径</td><td>${v6Esc(strategy.path_type || d.path_type || '—')}</td></tr>
        <tr><td>命中数</td><td class="${hits.length > 0 ? 'text-green' : 'text-muted'}">${hits.length}</td></tr>
        <tr><td>失败数</td><td class="${failed.length > 0 ? 'text-yellow' : ''}">${failed.length}</td></tr>
      </table>
      <div style="margin-top:12px">
        <div class="section-title">命中股票（${hits.length} 只）</div>
        <div style="font-size:12px;word-break:break-all;color:var(--fg)">
          ${hits.length ? v6Esc(hits.join(', ')) : '<span class="text-muted">无命中</span>'}
        </div>
      </div>
      ${failed.length ? `<div style="margin-top:8px">
        <div class="section-title">失败代码</div>
        <div style="font-size:12px;color:var(--yellow)">${v6Esc(failed.join(', '))}</div>
      </div>` : ''}`;
  }

  // ── 载入为当前策略（不自动运行） ──────────────────────────────────
  window._rptLoad = async function (runId) {
    try {
      const url = V6API.runs.replace(/\/?$/, '/') + runId + '/params';
      const r   = await fetch(url, { cache: 'no-store' });
      const d   = await r.json();
      const strategy = d.strategy || d.params || {};
      V6Common.V6Store.set('v6op_strategy_draft', strategy);
      localStorage.setItem('v6op_strategy_draft', JSON.stringify(strategy));
      v6Alert('rpt-alerts', 'ok', `已将 ${runId} 的参数载入策略台草稿（打开策略台可恢复）`);
    } catch (e) {
      v6Alert('rpt-alerts', 'danger', '载入失败：' + e.message, false);
    }
  };

  // ── 跳转到对比页 ──────────────────────────────────────────────────
  function _goCompare() {
    const checked = Array.from(document.querySelectorAll('.rpt-chk:checked'))
      .map(function (c) { return parseInt(c.dataset.idx, 10); });
    const ids = checked.map(function (i) { return _filtered()[i]?.run_id; }).filter(Boolean);
    if (ids.length < 2) { v6Alert('rpt-alerts', 'warn', '请至少勾选 2 份报告'); return; }
    if (ids.length > 4) { v6Alert('rpt-alerts', 'warn', '最多同时对比 4 份'); return; }
    window.location.href = '/compare.html?runs=' + encodeURIComponent(ids.join(','));
  }

})();
