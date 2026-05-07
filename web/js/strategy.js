/**
 * strategy.js — V6OP 策略台增强层
 * 加载顺序：common.js → app.js → strategy.js
 *
 * 功能：
 * - 初始化多页面导航
 * - 拦截 btn-run，显示启动预览 Modal
 * - 实时刷新 Query 预览区
 * - 策略模板保存 / 恢复 / 删除
 * - 最近输入同步（来自输入工坊）
 */
'use strict';

(function () {
  const TEMPLATE_KEY = 'v6op_strategy_templates';
  const RECENT_KEY   = 'v6op_recent_inputs';

  // ── 启动 ────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    // 导航
    V6Common.V6Nav.init('strategy');

    // 等待 app.js DOMContentLoaded 完成后再覆盖
    setTimeout(function () {
      _interceptRunButton();
      _bindTemplateButton();
      _bindPreviewRefresh();
      _initRecentInputs();
      _updateQueryPreview();
    }, 50);

    // 监听 wencai-query / sector-query 变动以实时刷新预览
    ['wencai-query', 'sector-query', 'manual-codes'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', _updateQueryPreview);
    });
    document.querySelectorAll('input[name="source-type"], input[name="path-type"]')
      .forEach(function (r) { r.addEventListener('change', _updateQueryPreview); });
    document.getElementById('skill-list')?.addEventListener('change', _updateQueryPreview);
    document.addEventListener('v6op:strategy-state-change', _updateQueryPreview);
    _bindPreviewInputs();
  });

  // ── 拦截 Run 按钮，先显示预览 ──────────────────────────────────────
  function _interceptRunButton() {
    const btn = document.getElementById('btn-run');
    if (!btn) return;
    // 克隆替换，移除 app.js 绑定的旧监听器
    const fresh = btn.cloneNode(true);
    btn.parentNode.replaceChild(fresh, btn);
    fresh.addEventListener('click', function () {
      _showRunPreview();
    });
  }

  function _showRunPreview() {
    // 使用 app.js 暴露的 buildStrategy（全局 function）
    let strategy;
    try {
      strategy = buildStrategy(); // from app.js
    } catch (e) {
      alert('策略构建失败：' + e.message);
      return;
    }
    if (!strategy) return;

    // 记录本次 query 到最近输入
    const rawQuery = document.getElementById('wencai-query')?.value ||
                     document.getElementById('sector-query')?.value || '';
    if (rawQuery.trim()) {
      const sourceType = document.querySelector('input[name="source-type"]:checked')?.value || 'manual';
      _pushRecentInput(rawQuery.trim(), sourceType === 'wencai' ? 'Phase B' : 'manual');
    }

    // 填充预览表格
    const tbody = document.getElementById('run-preview-body');
    if (!tbody) return;

    const src = strategy.source || {};
    const skills = (strategy.skills || []).join(', ') || '—';
    const path = strategy.path_type || '—';
    const bridge = strategy.bridge
      ? `${strategy.bridge.mode} | ${strategy.bridge.wencai_query || '—'}`
      : '未启用';
    const sect = src.sector_linkage || {};
    const sectLink = sect.enabled
      ? `板块联动 ✓ (${(sect.confirmed_sectors || []).join(', ')})`
      : '—';
    const sourceLimitText = (src.limit == null || String(src.limit) === '0')
      ? '不限（不截断）'
      : String(src.limit);
    const runScopeLimit = Number(strategy.run_scope_limit || 0);
    const runScopeText = runScopeLimit > 0 ? `测试 ${runScopeLimit}` : '全量';

    const rows = [
      ['来源类型',   src.type || '—'],
      ['来源 Query', src.query || '—'],
      ['来源档位', sourceLimitText],
      ['运行规模', runScopeText],
      ['板块联动',   sectLink],
      ['技能链路',   skills],
      ['执行路径',   path],
      ['Bridge',     bridge],
    ];
    tbody.innerHTML = rows.map(function ([k, v]) {
      return `<tr><td>${V6Common.v6Esc(k)}</td><td>${V6Common.v6Esc(v)}</td></tr>`;
    }).join('');

    // 存策略对象，供确认时使用
    window._pendingStrategy = strategy;

    const overlay = document.getElementById('run-preview-overlay');
    if (overlay) overlay.classList.remove('hidden');

    // 绑定确认 / 取消
    document.getElementById('btn-preview-cancel')?.addEventListener('click', _closePreview, { once: true });
    document.getElementById('btn-preview-confirm')?.addEventListener('click', function () {
      _closePreview();
      _doRun(window._pendingStrategy);
    }, { once: true });
  }

  function _closePreview() {
    const overlay = document.getElementById('run-preview-overlay');
    if (overlay) overlay.classList.add('hidden');
  }

  function _doRun(strategy) {
    // 触发 app.js 的运行逻辑
    // app.js 的 bindRunButton 监听 btn-run 但已被替换
    // 直接重现 app.js _doRun 逻辑：POST /api/run
    const btn = document.getElementById('btn-run');
    if (btn) btn.disabled = true;
    if (typeof clearResult === 'function') clearResult();
    if (typeof resetRunPollingState === 'function') resetRunPollingState();
    if (typeof logClear === 'function') logClear();
    setRunningState(true);  // app.js 全局函数
    logLine('INFO', '策略台：启动管道…');

    fetch(V6Common.V6API.run, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(strategy),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.run_id) {
          const rid = document.getElementById('run-id');
          if (rid) rid.textContent = data.run_id;
        }
        if (data.error) {
          logLine('ERROR', '启动失败：' + data.error);
          setRunningState(false);
        } else {
          logLine('INFO', '已提交，run_id=' + data.run_id);
          startPoll();  // app.js 全局
        }
      })
      .catch(function (e) {
        logLine('ERROR', '请求失败：' + e.message);
        setRunningState(false);
      });
  }

  // ── Query 预览实时刷新 ─────────────────────────────────────────────
  function _bindPreviewRefresh() {
    const btn = document.getElementById('btn-refresh-preview');
    if (btn) btn.addEventListener('click', _updateQueryPreview);
  }

  function _bindPreviewInputs() {
    [
      'wencai-query', 'sector-query', 'manual-codes',
      'wencai-limit', 'sector-top-n', 'all-a-limit', 'run-scope-limit',
      'bridge-enabled', 'bridge-mode', 'bridge-query', 'bridge-limit',
      'wm-btn-stock', 'wm-btn-sector', 'btn-confirm-sectors',
    ].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el) return;
      ['input', 'change', 'click'].forEach(function (eventName) {
        el.addEventListener(eventName, function () {
          setTimeout(_updateQueryPreview, 0);
        });
      });
    });
  }

  function _setPreview(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text || '—';
  }

  function _updateQueryPreview() {
    const sourceType = document.querySelector('input[name="source-type"]:checked')?.value || 'manual';
    const pathType   = document.querySelector('input[name="path-type"]:checked')?.value || 'parallel_and';

    function selectedText(id, fallback) {
      const el = document.getElementById(id);
      const value = el?.value || '';
      if (value === '0') return '不限';
      return el?.selectedOptions?.[0]?.textContent || value || fallback || '';
    }

    let sourceStr = '';
    if (sourceType === 'manual') {
      const codes = (document.getElementById('manual-codes')?.value || '').trim();
      const count = codes ? codes.split(/[\s,，,]+/).filter(Boolean).length : 0;
      sourceStr = `手动输入代码 | ${count} 只`;
    } else if (sourceType === 'all_a') {
      sourceStr = `全 A 股 | ${selectedText('all-a-limit', '不限')}`;
    } else {
      const mode = typeof getWencaiMode === 'function'
        ? getWencaiMode()
        : (document.getElementById('wm-btn-sector')?.classList.contains('active') ? 'sector' : 'stock');
      const query = document.getElementById('wencai-query')?.value || '';
      const limit = selectedText('wencai-limit', '不限');
      if (mode === 'sector') {
        const sectors = typeof getConfirmedSectors === 'function' ? getConfirmedSectors() : [];
        const sectorQuery = document.getElementById('sector-query')?.value || '';
        sourceStr = `问财板块联动\nPhase A: ${sectorQuery || '未填写'}\n已确认板块: ${sectors.join('、') || '未确认'}\nPhase B: ${query || '未填写'}\n档位: ${limit}`;
      } else {
        sourceStr = `问财个股 | ${query || '未填写'}\n档位: ${limit}`;
      }
    }

    const checked = Array.from(document.querySelectorAll('#skill-list input[type=checkbox]:checked'))
      .map(function (c) { return c.value; });
    const skillsStr = checked.length ? checked.join(' -> ') : '未选择技能';

    const bridgeOn = !!document.getElementById('bridge-enabled')?.checked;
    const bridgeQ  = document.getElementById('bridge-query')?.value || '';
    const bridgeMode = selectedText('bridge-mode', '');
    const pathStr = bridgeOn
      ? `${pathType} | Bridge(${bridgeMode}): ${bridgeQ || '未填写'}`
      : pathType;
    const runScopeEl = document.getElementById('run-scope-limit');
    const runScope = runScopeEl?.selectedOptions?.[0]?.textContent || '全量';

    _setPreview('preview-source', sourceStr);
    _setPreview('preview-skills', skillsStr);
    _setPreview('preview-path', `${pathStr}\n运行规模: ${runScope}`);
  }

  // ── 策略模板保存 / 恢复 ────────────────────────────────────────────
  function _bindTemplateButton() {
    const btn = document.getElementById('btn-save-template');
    if (!btn) return;
    btn.addEventListener('click', function () {
      _renderTemplateList();
      const overlay = document.getElementById('template-save-overlay');
      if (overlay) overlay.classList.remove('hidden');
    });

    document.getElementById('btn-template-cancel')?.addEventListener('click', function () {
      const overlay = document.getElementById('template-save-overlay');
      if (overlay) overlay.classList.add('hidden');
    });

    document.getElementById('btn-template-save')?.addEventListener('click', _saveCurrentTemplate);
  }

  function _saveCurrentTemplate() {
    const nameEl = document.getElementById('template-name-input');
    const name   = (nameEl?.value || '').trim();
    if (!name) { alert('请输入模板名称'); return; }

    let strategy;
    try { strategy = buildStrategy(); } catch (e) { alert('策略构建失败：' + e.message); return; }
    if (!strategy) return;

    const templates = V6Common.V6Store.get(TEMPLATE_KEY, []);
    const existing  = templates.findIndex(function (t) { return t.name === name; });
    const tpl = {
      name,
      saved_at: new Date().toISOString(),
      strategy,
      // extra UI state
      source_type: document.querySelector('input[name="source-type"]:checked')?.value || 'manual',
      wencai_mode: window._wencaiMode || 'stock',
      confirmed_sectors: window._confirmedSectors || [],
    };
    if (existing >= 0) templates[existing] = tpl;
    else templates.unshift(tpl);
    V6Common.V6Store.set(TEMPLATE_KEY, templates.slice(0, 20));
    if (nameEl) nameEl.value = '';
    _renderTemplateList();
  }

  function _renderTemplateList() {
    const container = document.getElementById('template-list');
    if (!container) return;
    const templates = V6Common.V6Store.get(TEMPLATE_KEY, []);
    if (!templates.length) {
      container.innerHTML = '<span class="text-muted" style="font-size:11px">暂无保存模板</span>';
      return;
    }
    container.innerHTML = templates.map(function (t, i) {
      const date = V6Common.v6FmtDate(t.saved_at);
      return `<div class="template-item">
        <span class="template-item-name">${V6Common.v6Esc(t.name)}</span>
        <span class="template-item-meta">${V6Common.v6Esc(date)}</span>
        <button class="btn btn-sm" onclick="window._restoreTpl(${i})" type="button">恢复</button>
        <button class="btn btn-sm" style="color:var(--red)"
          onclick="window._deleteTpl(${i})" type="button">✕</button>
      </div>`;
    }).join('');
  }

  window._restoreTpl = function (idx) {
    const templates = V6Common.V6Store.get(TEMPLATE_KEY, []);
    const tpl = templates[idx];
    if (!tpl) return;
    // 恢复 source_type
    const radio = document.querySelector(`input[name="source-type"][value="${tpl.source_type}"]`);
    if (radio) { radio.checked = true; radio.dispatchEvent(new Event('change')); }
    // 恢复 wencai mode
    if (tpl.wencai_mode) setWencaiMode(tpl.wencai_mode, true);  // app.js global
    // 恢复 params via _applyRestoredParams (app.js)
    if (typeof _applyRestoredParams === 'function') _applyRestoredParams(tpl.strategy);
    // 关闭 modal
    const overlay = document.getElementById('template-save-overlay');
    if (overlay) overlay.classList.add('hidden');
    _updateQueryPreview();
  };

  window._deleteTpl = function (idx) {
    if (!confirm('删除该模板？')) return;
    const templates = V6Common.V6Store.get(TEMPLATE_KEY, []);
    templates.splice(idx, 1);
    V6Common.V6Store.set(TEMPLATE_KEY, templates);
    _renderTemplateList();
  };

  // ── 最近输入 ───────────────────────────────────────────────────────
  function _pushRecentInput(text, context) {
    V6Common.V6Store.push(RECENT_KEY, {
      text,
      context,
      at: new Date().toISOString(),
    }, 30);
    _initRecentInputs();
  }

  function _initRecentInputs() {
    const container = document.getElementById('recent-inputs-list');
    if (!container) return;
    const items = V6Common.V6Store.get(RECENT_KEY, []);
    if (!items.length) {
      container.innerHTML = '<span class="text-muted" style="font-size:11px">暂无最近输入</span>';
      return;
    }
    container.innerHTML = items.slice(0, 8).map(function (item, i) {
      return `<div class="recent-item">
        <span class="recent-tag">${V6Common.v6Esc(item.context || '—')}</span>
        <span class="recent-item-text">${V6Common.v6Esc(item.text)}</span>
        <button class="btn btn-sm" style="font-size:10px"
          onclick="window._fillFromRecent(${i})" type="button">填入</button>
      </div>`;
    }).join('');
  }

  window._fillFromRecent = function (idx) {
    const items = V6Common.V6Store.get(RECENT_KEY, []);
    const item  = items[idx];
    if (!item) return;
    const qEl = document.getElementById('wencai-query');
    if (qEl) {
      qEl.value = item.text;
      qEl.dispatchEvent(new Event('input'));
    }
    _updateQueryPreview();
  };

  // ── 接收来自输入工坊的草稿 ─────────────────────────────────────────
  window.addEventListener('storage', function (e) {
    if (e.key === 'v6op_strategy_draft') {
      const draft = V6Common.V6Store.get('v6op_strategy_draft');
      if (!draft) return;
      if (draft.phase_a_query) {
        const el = document.getElementById('sector-query');
        if (el) el.value = draft.phase_a_query;
      }
      if (draft.phase_b_query) {
        const el = document.getElementById('wencai-query');
        if (el) el.value = draft.phase_b_query;
      }
      if (draft.wencai_mode) setWencaiMode(draft.wencai_mode, true);
      _updateQueryPreview();
      V6Common.v6Alert('center-alerts', 'ok', '已从输入工坊同步草稿');
    }
  });

})();
