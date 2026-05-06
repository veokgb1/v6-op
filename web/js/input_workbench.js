/**
 * input_workbench.js — V6OP 输入工坊主逻辑
 * 依赖：common.js → prompt_bank.js → input_workbench.js
 */
'use strict';

(function () {
  const { v6Esc, V6Store, v6Alert, v6FmtDate } = V6Common;

  // ── 条件积木语料 ────────────────────────────────────────────────────
  const CHIPS = {
    topic: [
      '人工智能', '半导体', '算力', '机器人', '低空经济',
      '新能源', '医药', '军工', '消费', '化工',
    ],
    style: [
      { label: '激进（量价突破）',  text: '今日涨幅大于5%，且换手率大于5%' },
      { label: '稳健（趋势）',      text: '近20日涨幅大于10%，且MA20向上' },
      { label: '低吸（回调）',      text: '近5日跌幅大于8%，且近60日涨幅大于20%' },
      { label: '突破（成交放量）',  text: '今日成交额大于昨日2倍，且涨幅大于3%' },
      { label: '趋势（创新高）',    text: '近5日创60日新高，且换手率大于2%' },
      { label: '防守（低波动）',    text: '近20日振幅小于15%，且近5日跌幅小于3%' },
    ],
    fund: [
      '今日主力净流入大于0',
      '近3日主力资金净流入大于0',
      '近5日主力资金净流入大于1亿',
      '今日成交额排名前100',
      '今日换手率大于3%',
    ],
    risk: [
      '非ST',
      '非停牌',
      '上市超过1年',
      '流通市值大于20亿',
      '流通市值小于200亿',
      '近5日涨幅小于30%',
    ],
  };

  const ALL_TYPES = ['stock', 'sector', 'bridge', 'report'];
  const ALL_TAGS  = ['激进', '保守', '科技', '资金', '低吸', '突破', '趋势',
                     '防守', '小盘', '中盘', '板块', '轮动', '题材', '风险'];

  // ── 状态 ──────────────────────────────────────────────────────────
  let _searchQuery  = '';
  let _typeFilter   = '';
  let _tagFilter    = '';
  let _composerParts = [];

  // ── 入口 ──────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    V6Common.V6Nav.init('input');
    _initMatrix();
    _initComposer();
    _initRecent();
    _initTemplates();
    _initImportExport();
    _initTabNav();
  });

  // ── Tab 切换 ───────────────────────────────────────────────────────
  function _initTabNav() {
    document.querySelectorAll('.iw-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const target = btn.dataset.tab;
        document.querySelectorAll('.iw-tab').forEach(function (b) {
          b.classList.toggle('iw-tab-active', b === btn);
        });
        document.querySelectorAll('.iw-panel').forEach(function (p) {
          p.classList.toggle('iw-panel-hidden', p.id !== 'iwp-' + target);
        });
      });
    });
  }

  // ════════════════════════════════════════════════════════════════════
  // § 1. 提示词矩阵
  // ════════════════════════════════════════════════════════════════════
  function _initMatrix() {
    _bindMatrixFilters();
    _renderMatrix();
  }

  function _bindMatrixFilters() {
    const searchEl = document.getElementById('pm-search');
    if (searchEl) searchEl.addEventListener('input', function () {
      _searchQuery = this.value;
      _renderMatrix();
    });

    document.querySelectorAll('.pm-type-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        _typeFilter = _typeFilter === btn.dataset.type ? '' : btn.dataset.type;
        document.querySelectorAll('.pm-type-btn').forEach(function (b) {
          b.classList.toggle('pm-type-active', b.dataset.type === _typeFilter);
        });
        _renderMatrix();
      });
    });

    document.querySelectorAll('.pm-tag-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        _tagFilter = _tagFilter === btn.dataset.tag ? '' : btn.dataset.tag;
        document.querySelectorAll('.pm-tag-btn').forEach(function (b) {
          b.classList.toggle('pm-tag-active', b.dataset.tag === _tagFilter);
        });
        _renderMatrix();
      });
    });

    document.getElementById('btn-pm-new')?.addEventListener('click', _showEditForm);
  }

  function _renderMatrix() {
    const container = document.getElementById('pm-cards');
    if (!container) return;
    const all     = PromptBank.load();
    const results = PromptBank.search(all, _searchQuery, _typeFilter, _tagFilter);

    if (!results.length) {
      container.innerHTML = '<div class="text-muted" style="padding:20px 0">没有匹配的提示词</div>';
      return;
    }

    container.innerHTML = results.map(function (p) {
      const tags = (p.tags || []).map(function (t) {
        return `<span class="pm-card-tag">${v6Esc(t)}</span>`;
      }).join('');
      const typeColors = { stock: 'text-green', sector: 'text-blue', bridge: 'text-yellow', report: 'var(--muted)' };
      const pinIcon = p.pinned ? '📌 ' : '';
      return `<div class="pm-card" data-id="${v6Esc(p.id)}">
        <div class="pm-card-header">
          <span class="pm-card-title">${pinIcon}${v6Esc(p.title)}</span>
          <span class="pm-card-type ${typeColors[p.type] || ''}">${v6Esc(p.type)}</span>
        </div>
        <div class="pm-card-body">${v6Esc(p.body)}</div>
        <div class="pm-card-footer">
          <span class="pm-card-tags">${tags}</span>
          <span class="pm-card-meta">使用 ${p.use_count || 0} 次 | ${v6FmtDate(p.created_at)}</span>
        </div>
        <div class="pm-card-actions">
          <button class="btn btn-sm" onclick="_pmSend('${v6Esc(p.id)}','phase_a')" type="button">→ Phase A</button>
          <button class="btn btn-sm" onclick="_pmSend('${v6Esc(p.id)}','phase_b')" type="button">→ Phase B</button>
          <button class="btn btn-sm" onclick="_pmSend('${v6Esc(p.id)}','bridge')"  type="button">→ Bridge</button>
          <button class="btn btn-sm" onclick="_pmSend('${v6Esc(p.id)}','report')"  type="button">→ 报告词</button>
          <span style="flex:1"></span>
          <button class="btn btn-sm" onclick="_pmPin('${v6Esc(p.id)}')"    type="button">${p.pinned ? '取消置顶' : '置顶'}</button>
          <button class="btn btn-sm" onclick="_pmEdit('${v6Esc(p.id)}')"   type="button">编辑</button>
          <button class="btn btn-sm" style="color:var(--red)"
            onclick="_pmDelete('${v6Esc(p.id)}')" type="button">删除</button>
        </div>
      </div>`;
    }).join('');
  }

  window._pmSend = function (id, target) {
    const all = PromptBank.load();
    const p   = all.find(function (x) { return x.id === id; });
    if (!p) return;
    PromptBank.sendToDraft(p, target);
    v6Alert('iw-alerts', 'ok', `已发送到 ${target}（策略台将自动同步）`);
    // 同时填入本页预览区
    const previewEl = document.getElementById('iw-draft-preview');
    if (previewEl) {
      previewEl.innerHTML += `<div class="recent-item">
        <span class="recent-tag">${v6Esc(target)}</span>
        <span class="recent-item-text">${v6Esc(p.body)}</span></div>`;
    }
    _renderMatrix();
  };

  window._pmPin = function (id) {
    PromptBank.togglePin(id);
    _renderMatrix();
  };

  window._pmDelete = function (id) {
    if (!confirm('删除该提示词？')) return;
    PromptBank.remove(id);
    _renderMatrix();
  };

  window._pmEdit = function (id) {
    const all = PromptBank.load();
    const p   = all.find(function (x) { return x.id === id; });
    if (p) _showEditForm(p);
  };

  function _showEditForm(existing) {
    const modal = document.getElementById('pm-edit-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    const p = existing || {};
    document.getElementById('pme-title').value  = p.title || '';
    document.getElementById('pme-type').value   = p.type  || 'stock';
    document.getElementById('pme-tags').value   = (p.tags || []).join(', ');
    document.getElementById('pme-body').value   = p.body  || '';
    document.getElementById('pme-id').value     = p.id    || '';
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('btn-pme-save')?.addEventListener('click', function () {
      const id    = document.getElementById('pme-id')?.value   || '';
      const title = document.getElementById('pme-title')?.value.trim() || '';
      const type  = document.getElementById('pme-type')?.value || 'stock';
      const tags  = (document.getElementById('pme-tags')?.value || '').split(/[,，\s]+/).filter(Boolean);
      const body  = document.getElementById('pme-body')?.value.trim() || '';
      if (!title || !body) { alert('请填写标题和正文'); return; }
      PromptBank.add({
        id:         id || ('user_' + Date.now()),
        type, title, tags, body,
        use_count:  0,
        pinned:     false,
        created_at: new Date().toISOString(),
      });
      document.getElementById('pm-edit-modal')?.classList.add('hidden');
      _renderMatrix();
    });
    document.getElementById('btn-pme-cancel')?.addEventListener('click', function () {
      document.getElementById('pm-edit-modal')?.classList.add('hidden');
    });
  });

  // ════════════════════════════════════════════════════════════════════
  // § 2. 条件积木 Composer
  // ════════════════════════════════════════════════════════════════════
  function _initComposer() {
    const container = document.getElementById('composer-chips');
    if (!container) return;

    const sections = [
      { label: '题材', key: 'topic', items: CHIPS.topic.map(function (t) { return { label: t, text: `属于${t}概念` }; }) },
      { label: '风格', key: 'style', items: CHIPS.style },
      { label: '资金', key: 'fund',  items: CHIPS.fund.map(function (t) { return { label: t, text: t }; }) },
      { label: '风险', key: 'risk',  items: CHIPS.risk.map(function (t) { return { label: t, text: t }; }) },
    ];

    container.innerHTML = sections.map(function (sec) {
      const chips = sec.items.map(function (item, i) {
        return `<span class="composer-chip" data-key="${v6Esc(sec.key)}" data-idx="${i}"
          data-text="${v6Esc(item.text)}">${v6Esc(item.label)}</span>`;
      }).join('');
      return `<div class="composer-section">
        <div class="composer-section-label">${v6Esc(sec.label)}</div>
        <div class="composer-chips-row">${chips}</div>
      </div>`;
    }).join('');

    container.addEventListener('click', function (e) {
      const chip = e.target.closest('.composer-chip');
      if (!chip) return;
      chip.classList.toggle('composer-chip-active');
      _recomposeQuery();
    });

    document.getElementById('btn-composer-clear')?.addEventListener('click', function () {
      document.querySelectorAll('.composer-chip-active').forEach(function (c) {
        c.classList.remove('composer-chip-active');
      });
      _recomposeQuery();
    });
    document.getElementById('btn-composer-to-a')?.addEventListener('click', function () {
      _sendComposedQuery('phase_a');
    });
    document.getElementById('btn-composer-to-b')?.addEventListener('click', function () {
      _sendComposedQuery('phase_b');
    });
  }

  function _recomposeQuery() {
    const active = Array.from(document.querySelectorAll('.composer-chip-active'))
      .map(function (c) { return c.dataset.text; });
    const composed = active.join('，且');
    const el = document.getElementById('composer-output');
    if (el) el.value = composed;
  }

  function _sendComposedQuery(target) {
    const el    = document.getElementById('composer-output');
    const query = el?.value.trim() || '';
    if (!query) { v6Alert('iw-alerts', 'warn', '请先选择条件'); return; }
    const draft = V6Common.V6Store.get('v6op_strategy_draft', {});
    if (target === 'phase_a') { draft.phase_a_query = query; draft.wencai_mode = 'sector'; }
    else                      { draft.phase_b_query = query; draft.wencai_mode = 'stock';  }
    V6Common.V6Store.set('v6op_strategy_draft', draft);
    localStorage.setItem('v6op_strategy_draft', JSON.stringify(draft));
    // 记录最近使用
    V6Common.V6Store.push('v6op_recent_inputs', { text: query, context: target, at: new Date().toISOString() }, 30);
    v6Alert('iw-alerts', 'ok', `已发送到 ${target}`);
  }

  // ════════════════════════════════════════════════════════════════════
  // § 3. 最近使用
  // ════════════════════════════════════════════════════════════════════
  function _initRecent() {
    _renderRecent();
  }

  function _renderRecent() {
    const container = document.getElementById('recent-list');
    if (!container) return;
    const items = PromptBank.getRecent();
    if (!items.length) {
      container.innerHTML = '<div class="text-muted" style="padding:12px 0">暂无最近使用</div>';
      return;
    }
    container.innerHTML = items.map(function (item, i) {
      return `<div class="recent-item" data-idx="${i}">
        <span class="recent-tag">${v6Esc(item.context || '—')}</span>
        <span class="recent-item-text">${v6Esc(item.text)}</span>
        <span class="recent-item-meta">${v6FmtDate(item.at)}</span>
        <div style="display:flex;gap:4px;flex-shrink:0">
          <button class="btn btn-sm" onclick="_recentToA(${i})"    type="button">→ A</button>
          <button class="btn btn-sm" onclick="_recentToB(${i})"    type="button">→ B</button>
          <button class="btn btn-sm" onclick="_recentCopy(${i})"   type="button">复制</button>
          <button class="btn btn-sm" style="color:var(--red)"
            onclick="_recentDel(${i})" type="button">✕</button>
        </div>
      </div>`;
    }).join('');
  }

  window._recentToA = function (i) {
    const item = PromptBank.getRecent()[i];
    if (!item) return;
    const draft = V6Common.V6Store.get('v6op_strategy_draft', {});
    draft.phase_a_query = item.text; draft.wencai_mode = 'sector';
    localStorage.setItem('v6op_strategy_draft', JSON.stringify(draft));
    v6Alert('iw-alerts', 'ok', '已发送到 Phase A');
  };
  window._recentToB = function (i) {
    const item = PromptBank.getRecent()[i];
    if (!item) return;
    const draft = V6Common.V6Store.get('v6op_strategy_draft', {});
    draft.phase_b_query = item.text; draft.wencai_mode = 'stock';
    localStorage.setItem('v6op_strategy_draft', JSON.stringify(draft));
    v6Alert('iw-alerts', 'ok', '已发送到 Phase B');
  };
  window._recentCopy = function (i) {
    const item = PromptBank.getRecent()[i];
    if (item) navigator.clipboard?.writeText(item.text).catch(function () {});
  };
  window._recentDel = function (i) {
    PromptBank.deleteRecent(i);
    _renderRecent();
  };

  // ════════════════════════════════════════════════════════════════════
  // § 4. 策略模板
  // ════════════════════════════════════════════════════════════════════
  const TMPL_KEY = 'v6op_strategy_templates';

  function _initTemplates() {
    _renderTemplates();
    document.getElementById('btn-tmpl-open')?.addEventListener('click', function () {
      _renderTemplates();
    });
  }

  function _renderTemplates() {
    const container = document.getElementById('tmpl-list');
    if (!container) return;
    const templates = V6Common.V6Store.get(TMPL_KEY, []);
    if (!templates.length) {
      container.innerHTML = '<div class="text-muted" style="padding:12px 0">暂无保存模板</div>';
      return;
    }
    container.innerHTML = templates.map(function (t, i) {
      const src    = t.strategy?.source?.type || '—';
      const skills = (t.strategy?.skills || []).join('+') || '—';
      const path   = t.strategy?.path_type || '—';
      return `<div class="template-item">
        <div>
          <div class="template-item-name">${v6Esc(t.name)}</div>
          <div class="template-item-meta">${v6Esc(src)} | ${v6Esc(skills)} | ${v6Esc(path)} | ${v6FmtDate(t.saved_at)}</div>
        </div>
        <button class="btn btn-sm" onclick="_tmplLoad(${i})"   type="button">恢复到策略台</button>
        <button class="btn btn-sm" onclick="_tmplCopy(${i})"   type="button">复制</button>
        <button class="btn btn-sm" style="color:var(--red)"
          onclick="_tmplDelete(${i})" type="button">删除</button>
      </div>`;
    }).join('');
  }

  window._tmplLoad = function (i) {
    const templates = V6Common.V6Store.get(TMPL_KEY, []);
    const t = templates[i];
    if (!t) return;
    // 把模板写入 draft，策略台 storage 事件会拿到
    V6Common.V6Store.set('v6op_strategy_draft', t.strategy || {});
    localStorage.setItem('v6op_strategy_draft', JSON.stringify(t.strategy || {}));
    v6Alert('iw-alerts', 'ok', `模板"${t.name}"已发送到策略台`);
  };
  window._tmplCopy = function (i) {
    const templates = V6Common.V6Store.get(TMPL_KEY, []);
    const t = templates[i];
    if (!t) return;
    const copy = Object.assign({}, t, {
      name: t.name + '_副本',
      saved_at: new Date().toISOString(),
    });
    templates.unshift(copy);
    V6Common.V6Store.set(TMPL_KEY, templates.slice(0, 20));
    _renderTemplates();
  };
  window._tmplDelete = function (i) {
    if (!confirm('删除该模板？')) return;
    const templates = V6Common.V6Store.get(TMPL_KEY, []);
    templates.splice(i, 1);
    V6Common.V6Store.set(TMPL_KEY, templates);
    _renderTemplates();
  };

  // ════════════════════════════════════════════════════════════════════
  // § 5. 导入 / 导出
  // ════════════════════════════════════════════════════════════════════
  function _initImportExport() {
    document.getElementById('btn-import')?.addEventListener('click', function () {
      const text = document.getElementById('import-textarea')?.value || '';
      try {
        const items = PromptBank.importText(text);
        items.forEach(function (item) { PromptBank.add(item); });
        v6Alert('iw-alerts', 'ok', `成功导入 ${items.length} 条提示词`);
        document.getElementById('import-textarea').value = '';
        _renderMatrix();
      } catch (e) {
        v6Alert('iw-alerts', 'danger', '导入失败：' + e.message, false);
      }
    });

    document.getElementById('btn-export')?.addEventListener('click', function () {
      const all  = PromptBank.load();
      const json = PromptBank.exportJSON(all);
      const blob = new Blob([json], { type: 'application/json' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `v6op_prompt_bank_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

})();
