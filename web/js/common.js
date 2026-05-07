/**
 * common.js — V6OP 多页面共享工具模块
 * 加载顺序：每个页面第一个 <script>
 */
'use strict';

// ── API 端点注册表 ──────────────────────────────────────────────────────
const V6API = {
  health:         '/api/health',
  run:            '/api/run',
  result:         '/api/result',
  stream:         '/api/stream',
  abort:          '/api/abort',
  scanSectors:    '/api/scan_sectors',
  runs:           '/api/runs',
  wencaiStatus:   '/api/wencai/status',
  compareReports: '/api/reports/compare',
  promptBank:     '/api/prompt_bank',
  cacheSource:    '/api/cache/clear/source',
  cacheKline:     '/api/cache/clear/kline',
  cacheSkill:     '/api/cache/clear/skill',
};

// ── HTML 转义 ──────────────────────────────────────────────────────────
function v6Esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── 百分比格式 ─────────────────────────────────────────────────────────
function v6Pct(v) { return (v * 100).toFixed(1) + '%'; }

// ── localStorage 安全读写 ──────────────────────────────────────────────
const V6Store = {
  get(key, def = null) {
    try {
      const v = localStorage.getItem(key);
      return v === null ? def : JSON.parse(v);
    } catch { return def; }
  },
  set(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
  },
  remove(key) {
    try { localStorage.removeItem(key); } catch {}
  },
  push(key, item, maxLen = 30) {
    const arr = this.get(key, []);
    arr.unshift(item);
    this.set(key, arr.slice(0, maxLen));
  },
};

// ── 告警组件 ──────────────────────────────────────────────────────────
function v6Alert(containerId, type, msg, autoDismiss = true) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const icons = { warn: '⚠️', danger: '❌', info: 'ℹ️', ok: '✅' };
  const div = document.createElement('div');
  div.className = `alert alert-${type}`;
  div.innerHTML =
    `<span class="alert-icon">${icons[type] || 'ℹ️'}</span>` +
    `<span>${v6Esc(msg)}</span>` +
    `<button class="alert-close" onclick="this.parentNode.remove()">✕</button>`;
  el.prepend(div);
  if (autoDismiss && type !== 'danger') setTimeout(() => div.remove?.(), 5000);
}

// ── 导航 ──────────────────────────────────────────────────────────────
const V6Nav = {
  pages: [
    { key: 'strategy', label: '策略台',   href: '/strategy.html', icon: '⚡' },
    { key: 'input',    label: '输入工坊', href: '/input.html',    icon: '✏️' },
    { key: 'reports',  label: '报告中心', href: '/reports.html',  icon: '📊' },
    { key: 'compare',  label: '报告对比', href: '/compare.html',  icon: '⚖️' },
    { key: 'manage',   label: '管理中心',  href: '/manage.html',          icon: '⚙' },
    { key: 'canon',    label: '法典试点',  href: '/strategy_canon.html',  icon: '📖' },
  ],

  /** 渲染导航 HTML 并插入 #v6-nav 容器 */
  init(activePage) {
    const nav = document.getElementById('v6-nav');
    if (!nav) return;
    nav.innerHTML = this.pages.map(p => {
      const active = p.key === activePage ? ' v6-nav-active' : '';
      return `<a class="v6-nav-link${active}" href="${p.href}" data-page="${p.key}">${p.icon} ${p.label}</a>`;
    }).join('') +
    `<div class="v6-nav-spacer"></div>` +
    `<div id="v6-nav-health" class="v6-nav-health" title="后端状态">
       <span id="v6-nav-health-dot" class="health-dot"></span>
       <span id="v6-nav-health-label" class="health-label" style="font-size:11px">…</span>
     </div>`;
    this._startHealth();
  },

  _startHealth() {
    const check = async () => {
      const dot   = document.getElementById('v6-nav-health-dot');
      const label = document.getElementById('v6-nav-health-label');
      if (!dot) return;
      try {
        const r = await fetch(V6API.health, { cache: 'no-store' });
        if (r.ok) {
          dot.style.background   = 'var(--green)';
          label.textContent      = '后端在线';
        } else {
          dot.style.background   = 'var(--red)';
          label.textContent      = '后端异常';
        }
      } catch {
        dot.style.background     = 'var(--red)';
        label.textContent        = '后端离线';
      }
    };
    check();
    setInterval(check, 30000);
  },
};

// ── 日期格式化 ─────────────────────────────────────────────────────────
function v6FmtDate(iso) {
  if (!iso) return '—';
  return iso.replace('T', ' ').substring(0, 16);
}

// ── 简易 spinner 显示 ──────────────────────────────────────────────────
function v6SetLoading(btnId, loading, originalText) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  if (loading) btn.dataset.origText = btn.textContent;
  btn.textContent = loading ? '…' : (originalText || btn.dataset.origText || btn.textContent);
}

// ── 全局挂载 ──────────────────────────────────────────────────────────
window.V6Common = { V6API, v6Esc, v6Pct, V6Store, v6Alert, V6Nav, v6FmtDate, v6SetLoading };
