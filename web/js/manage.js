/**
 * manage.js — V6OP 管理中心（独立页面版）
 * 依赖：common.js
 */
'use strict';

(function () {
  const { V6API, v6Esc, v6Alert, v6FmtDate } = V6Common;

  document.addEventListener('DOMContentLoaded', function () {
    V6Common.V6Nav.init('manage');
    _initTabs();
    _loadHistory();
    _bindCache();
    _bindWencaiAuth();
    _bindSettings();
  });

  // ── Tab 切换 ────────────────────────────────────────────────────────
  function _initTabs() {
    document.querySelectorAll('.mgmt-tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const target = btn.dataset.mtab;
        document.querySelectorAll('.mgmt-tab-btn').forEach(function (b) {
          b.classList.toggle('mgmt-tab-active', b === btn);
        });
        document.querySelectorAll('.mgmt-tab-panel').forEach(function (p) {
          p.classList.toggle('mgmt-panel-hidden', p.id !== 'mtp-' + target);
        });
      });
    });
  }

  // ── 历史记录 ────────────────────────────────────────────────────────
  async function _loadHistory() {
    const container = document.getElementById('mgmt-history-list');
    if (!container) return;
    container.innerHTML = '<div class="text-muted" style="font-size:12px">加载中…</div>';
    try {
      const r = await fetch(V6API.runs, { cache: 'no-store' });
      const d = await r.json();
      const runs = d.runs || [];
      if (!runs.length) {
        container.innerHTML = '<div class="text-muted">暂无历史记录</div>';
        return;
      }
      container.innerHTML = runs.map(function (run) {
        const id      = run.run_id || '?';
        const src     = run.strategy?.source?.type || '—';
        const query   = (run.strategy?.source?.query || '').slice(0, 40);
        const hits    = run.final_hit_count ?? '?';
        const date    = v6FmtDate(run.started_at || '');
        return `<div class="mgmt-history-item">
          <div class="mgmt-run-id monospace">${v6Esc(id)}</div>
          <div class="mgmt-run-meta">${v6Esc(date)} | ${v6Esc(src)} | 命中 ${v6Esc(String(hits))}</div>
          ${query ? `<div class="mgmt-run-query">${v6Esc(query)}…</div>` : ''}
          <button class="btn btn-sm mt4" onclick="_mgmtRestore('${v6Esc(id)}')" type="button">恢复参数到策略台</button>
        </div>`;
      }).join('');
    } catch (e) {
      container.innerHTML = `<div class="text-red">加载失败：${v6Esc(e.message)}</div>`;
    }
  }

  window._mgmtRestore = async function (runId) {
    try {
      const url = V6API.runs.replace(/\/?$/, '/') + runId + '/params';
      const r   = await fetch(url, { cache: 'no-store' });
      const d   = await r.json();
      const strategy = d.strategy || d.params || {};
      V6Common.V6Store.set('v6op_strategy_draft', strategy);
      localStorage.setItem('v6op_strategy_draft', JSON.stringify(strategy));
      v6Alert('mgmt-alerts', 'ok', `已恢复 ${runId} 的参数到策略台草稿`);
    } catch (e) {
      v6Alert('mgmt-alerts', 'danger', '恢复失败：' + e.message, false);
    }
  };

  document.getElementById('btn-mgmt-reload-history')?.addEventListener('click', _loadHistory);

  // ── 缓存清理 ────────────────────────────────────────────────────────
  function _bindCache() {
    [
      ['btn-mgmt-clear-source', V6API.cacheSource, 'clear-source-result'],
      ['btn-mgmt-clear-kline',  V6API.cacheKline,  'clear-kline-result'],
      ['btn-mgmt-clear-skill',  V6API.cacheSkill,  'clear-skill-result'],
    ].forEach(function (spec) {
      const btnId = spec[0], url = spec[1], resultId = spec[2];
      document.getElementById(btnId)?.addEventListener('click', async function () {
        const res = document.getElementById(resultId);
        if (res) res.textContent = '清理中…';
        try {
          const r = await fetch(url, { method: 'POST', cache: 'no-store' });
          const d = await r.json();
          if (res) res.textContent = d.message || '完成';
        } catch (e) {
          if (res) res.textContent = '失败：' + e.message;
        }
      });
    });
  }

  // ── 问财授权检查 ────────────────────────────────────────────────────
  function _bindWencaiAuth() {
    document.getElementById('btn-mgmt-check-wencai')?.addEventListener('click', async function () {
      const el  = document.getElementById('mgmt-wencai-status');
      const btn = this;
      if (el) el.innerHTML = '<span class="text-muted">检查中…</span>';
      btn.disabled = true;
      try {
        const r    = await fetch(V6API.wencaiStatus, { cache: 'no-store' });
        const data = await r.json();
        if (!el) return;
        const rows = [
          ['pywencai 已安装',       data.pywencai_installed ? '✅ 是' : '❌ 否',
            data.pywencai_installed ? 'text-green' : 'text-red'],
          ['IWENCAI_API_KEY 已配置', data.env_key_present ? '✅ 是' : '⚠ 未配置',
            data.env_key_present ? 'text-green' : 'text-yellow'],
          ['当前状态', data.status || '—',
            data.status === 'ready' ? 'text-green' : 'text-yellow'],
        ];
        const rowsHtml = rows.map(function (row) {
          return `<div class="cov-item"><span class="cov-label">${v6Esc(row[0])}</span>`
            + `<span class="cov-value ${row[2]}">${v6Esc(row[1])}</span></div>`;
        }).join('');
        el.innerHTML = `<div class="coverage-grid">${rowsHtml}</div>` +
          (data.auth_mechanism
            ? `<div class="form-hint mt4">${v6Esc(data.auth_mechanism)}</div>` : '');
      } catch (e) {
        if (el) el.innerHTML = `<span class="text-red">检查失败：${v6Esc(e.message)}</span>`;
      } finally {
        btn.disabled = false;
      }
    });
  }

  // ── 系统设置 ────────────────────────────────────────────────────────
  function _bindSettings() {
    // 加载已保存设置
    const saved = V6Common.V6Store.get('v6op_settings', {});
    const pathEl = document.getElementById('mgmt-setting-path');
    const daysEl = document.getElementById('mgmt-setting-days');
    if (pathEl && saved.default_path) pathEl.value = saved.default_path;
    if (daysEl && saved.default_days) daysEl.value = saved.default_days;

    document.getElementById('btn-mgmt-save-settings')?.addEventListener('click', function () {
      const settings = {
        default_path: pathEl?.value || 'parallel_and',
        default_days: daysEl?.value || '365',
      };
      V6Common.V6Store.set('v6op_settings', settings);
      const tip = document.getElementById('mgmt-settings-tip');
      if (tip) { tip.style.display = ''; setTimeout(function () { tip.style.display = 'none'; }, 1500); }
    });
  }

})();
