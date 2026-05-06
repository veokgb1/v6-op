/**
 * prompt_bank.js — V6OP 提示词库数据管理
 * localStorage 持久化；后续可接 /api/prompt_bank
 */
'use strict';

(function () {
  const BANK_KEY    = 'v6op_prompt_bank';
  const RECENT_KEY  = 'v6op_recent_inputs';
  const DRAFT_KEY   = 'v6op_strategy_draft';

  // ── 默认内置提示词 ──────────────────────────────────────────────────
  const BUILTIN = [
    {
      id: 'builtin-ai-stock',
      type: 'stock',
      title: '人工智能个股 STABLE',
      tags: ['激进', '科技', '题材'],
      body: '属于人工智能板块，且近3日主力资金净流入大于0，且换手率大于3%',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
    {
      id: 'builtin-chip-stock',
      type: 'stock',
      title: '半导体个股-量价',
      tags: ['科技', '突破'],
      body: '属于半导体板块，且今日成交额排名前50，且涨幅大于3%',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
    {
      id: 'builtin-fund-flow',
      type: 'stock',
      title: '主力资金净流入-保守',
      tags: ['保守', '资金'],
      body: '近5日主力资金净流入大于1亿，且非ST，且上市超过1年',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
    {
      id: 'builtin-sector-tech',
      type: 'sector',
      title: '科技板块扫描-资金流入',
      tags: ['科技', '资金', '板块'],
      body: '今日主力资金净流入排名前10的行业板块，按净流入降序',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
    {
      id: 'builtin-sector-rotation',
      type: 'sector',
      title: '板块轮动-近3日',
      tags: ['板块', '轮动'],
      body: '近3日涨幅排名前10的概念板块，按涨幅降序',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
    {
      id: 'builtin-bridge-ai',
      type: 'bridge',
      title: 'Bridge - 人工智能约束',
      tags: ['科技', '题材'],
      body: '属于人工智能概念',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
    {
      id: 'builtin-bridge-fund',
      type: 'bridge',
      title: 'Bridge - 资金验证',
      tags: ['资金'],
      body: '近5日主力资金净流入大于0',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
    {
      id: 'builtin-report-综合',
      type: 'report',
      title: '综合分析提示词',
      tags: ['资金', '趋势'],
      body: '以下是今日量化筛选命中的股票列表：\n{codes}\n\n请对每只股票做综合技术面分析，包括：趋势方向、量能表现、关键支撑/压力位，并给出操作建议。',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
    {
      id: 'builtin-low-buy',
      type: 'stock',
      title: '低吸候选-回调中',
      tags: ['低吸', '保守'],
      body: '近5日跌幅大于8%，且近60日涨幅大于20%，且换手率大于2%，且非ST',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
    {
      id: 'builtin-small-cap',
      type: 'stock',
      title: '小盘弹性-激进',
      tags: ['激进', '小盘', '突破'],
      body: '流通市值小于50亿，且今日涨幅大于5%，且成交额大于1亿，且非ST',
      use_count: 0, pinned: false, created_at: '2026-01-01T00:00:00',
    },
  ];

  // ── 数据 CRUD ──────────────────────────────────────────────────────
  function load() {
    const saved = V6Common.V6Store.get(BANK_KEY, null);
    if (!saved || !saved.length) {
      const initial = BUILTIN.map(function (b) { return Object.assign({}, b); });
      V6Common.V6Store.set(BANK_KEY, initial);
      return initial;
    }
    // 合并新内置（按 id 去重）
    const ids = new Set(saved.map(function (p) { return p.id; }));
    const merged = saved.slice();
    BUILTIN.forEach(function (b) {
      if (!ids.has(b.id)) merged.push(Object.assign({}, b));
    });
    return merged;
  }

  function save(prompts) {
    V6Common.V6Store.set(BANK_KEY, prompts);
  }

  function add(prompt) {
    const prompts = load();
    const existing = prompts.findIndex(function (p) { return p.id === prompt.id; });
    if (existing >= 0) prompts[existing] = prompt;
    else prompts.unshift(prompt);
    save(prompts);
    return prompts;
  }

  function remove(id) {
    const prompts = load().filter(function (p) { return p.id !== id; });
    save(prompts);
    return prompts;
  }

  function togglePin(id) {
    const prompts = load();
    const p = prompts.find(function (x) { return x.id === id; });
    if (p) p.pinned = !p.pinned;
    save(prompts);
    return prompts;
  }

  function recordUse(id) {
    const prompts = load();
    const p = prompts.find(function (x) { return x.id === id; });
    if (p) p.use_count = (p.use_count || 0) + 1;
    save(prompts);
  }

  // ── 搜索 ──────────────────────────────────────────────────────────
  function search(prompts, query, typeFilter, tagFilter) {
    const q = (query || '').toLowerCase().trim();
    return prompts.filter(function (p) {
      if (typeFilter && p.type !== typeFilter) return false;
      if (tagFilter  && !(p.tags || []).includes(tagFilter)) return false;
      if (!q) return true;
      return p.title.toLowerCase().includes(q)
          || p.body.toLowerCase().includes(q)
          || (p.tags || []).some(function (t) { return t.toLowerCase().includes(q); });
    }).sort(function (a, b) {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
      return (b.use_count || 0) - (a.use_count || 0);
    });
  }

  // ── 导入 ──────────────────────────────────────────────────────────
  function importText(text) {
    text = text.trim();
    if (!text) throw new Error('内容为空');
    let items = [];

    // 尝试 JSON
    if (text.startsWith('[') || text.startsWith('{')) {
      try {
        const parsed = JSON.parse(text);
        items = Array.isArray(parsed) ? parsed : [parsed];
      } catch (e) {
        throw new Error('JSON 格式错误：' + e.message);
      }
    } else {
      // 纯文本：每段落一条，前两行为 title / tags
      const blocks = text.split(/\n{2,}/);
      items = blocks.map(function (block, i) {
        const lines = block.split('\n').map(function (l) { return l.trim(); });
        return {
          type:  'stock',
          title: lines[0] || ('导入 #' + (i + 1)),
          tags:  lines[1] ? lines[1].split(/[,，\s]+/).filter(Boolean) : [],
          body:  lines.slice(2).join('\n') || lines[0] || '',
        };
      });
    }

    // 验证并生成 id
    const results = [];
    items.forEach(function (item, i) {
      if (!item.body && !item.title) throw new Error('第 ' + (i + 1) + ' 条缺少 body 或 title');
      results.push({
        id:         'import_' + Date.now() + '_' + i,
        type:       item.type || 'stock',
        title:      item.title || ('导入 #' + (i + 1)),
        tags:       item.tags || [],
        body:       item.body || item.title,
        use_count:  0,
        pinned:     false,
        created_at: new Date().toISOString(),
      });
    });
    return results;
  }

  // ── 导出 ──────────────────────────────────────────────────────────
  function exportJSON(prompts) {
    return JSON.stringify(prompts, null, 2);
  }

  // ── 发送到策略草稿 ────────────────────────────────────────────────
  function sendToDraft(prompt, targetField) {
    recordUse(prompt.id);
    const draft = V6Common.V6Store.get(DRAFT_KEY, {});
    if (targetField === 'phase_a') {
      draft.phase_a_query = prompt.body;
      draft.wencai_mode   = 'sector';
    } else if (targetField === 'phase_b') {
      draft.phase_b_query = prompt.body;
      draft.wencai_mode   = 'stock';
    } else if (targetField === 'bridge') {
      draft.bridge_query  = prompt.body;
    } else if (targetField === 'report') {
      draft.report_prompt = prompt.body;
    }
    V6Common.V6Store.set(DRAFT_KEY, draft);
    // 通知策略台（cross-tab storage event）
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  }

  // ── 最近使用 ──────────────────────────────────────────────────────
  function getRecent() {
    return V6Common.V6Store.get(RECENT_KEY, []);
  }

  function deleteRecent(idx) {
    const items = getRecent();
    items.splice(idx, 1);
    V6Common.V6Store.set(RECENT_KEY, items);
    return items;
  }

  // ── 挂载到全局 ────────────────────────────────────────────────────
  window.PromptBank = {
    load, save, add, remove, togglePin, recordUse, search,
    importText, exportJSON, sendToDraft, getRecent, deleteRecent,
  };
})();
