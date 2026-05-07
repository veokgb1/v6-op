/**
 * canon_source_pilot.js — 问财法典来源区试点 (V6OP-CANON-002)
 * 原子化字段输入 + 三阶段状态机（IDLE → BUILDING → PREVIEWED → CONFIRMED）
 */
'use strict';

(function () {

  // ── A股原子定义 ──────────────────────────────────────────────────────────
  var ASTOCK_ATOMS = [
    // 基础过滤
    { id:'A-非ST',    group:'基础过滤', badge:'strong', label:'非ST',       type:'bool',   query:'非ST' },
    { id:'A-非停牌',  group:'基础过滤', badge:'strong', label:'非停牌',     type:'bool',   query:'非停牌' },
    { id:'A-上市天',  group:'基础过滤', badge:'strong', label:'上市超过',   type:'num_op',
      ops:['大于'], def_op:'大于', def_val:365, unit:'天', tmpl:'上市超过{val}天' },
    // 涨跌幅
    { id:'A-今涨',    group:'涨跌幅', badge:'strong', label:'今日涨幅',   type:'num_op',
      ops:['大于','小于'], def_op:'大于', def_val:3,  unit:'%', tmpl:'今日涨幅{op}{val}%' },
    { id:'A-3日涨',   group:'涨跌幅', badge:'strong', label:'近3日涨幅',  type:'num_op',
      ops:['大于','小于'], def_op:'大于', def_val:0,  unit:'%', tmpl:'近3日涨幅{op}{val}%' },
    { id:'A-5日涨',   group:'涨跌幅', badge:'strong', label:'近5日涨幅',  type:'num_op',
      ops:['大于','小于'], def_op:'大于', def_val:0,  unit:'%', tmpl:'近5日涨幅{op}{val}%' },
    { id:'A-20日涨',  group:'涨跌幅', badge:'strong', label:'近20日涨幅', type:'num_op',
      ops:['大于','小于'], def_op:'小于', def_val:5,  unit:'%', tmpl:'近20日涨幅{op}{val}%' },
    // 成交量价
    { id:'A-成交额',  group:'成交量价', badge:'strong', label:'今日成交额', type:'num_op',
      ops:['大于'], def_op:'大于', def_val:3,   unit:'亿', tmpl:'今日成交额大于{val}亿' },
    { id:'A-换手率',  group:'成交量价', badge:'strong', label:'今日换手率', type:'num_op',
      ops:['大于'], def_op:'大于', def_val:5,   unit:'%',  tmpl:'今日换手率大于{val}%' },
    { id:'A-量比',    group:'成交量价', badge:'strong', label:'今日量比',   type:'num_op',
      ops:['大于'], def_op:'大于', def_val:1.5, unit:'',   tmpl:'今日量比大于{val}' },
    // 市值
    { id:'A-流通市值', group:'市值', badge:'strong', label:'流通市值区间', type:'range',
      def_lo:30, def_hi:150, unit:'亿', tmpl:'流通市值在{lo}亿到{hi}亿之间' },
    { id:'A-总市值',   group:'市值', badge:'strong', label:'总市值区间',   type:'range',
      def_lo:50, def_hi:300, unit:'亿', tmpl:'总市值在{lo}亿到{hi}亿之间' },
    // 资金
    { id:'A-主力正', group:'资金', badge:'strong', label:'主力净流入为正', type:'bool',   query:'今日主力净流入为正' },
    { id:'A-主力额', group:'资金', badge:'strong', label:'主力净流入',     type:'num_op',
      ops:['大于'], def_op:'大于', def_val:1,   unit:'亿', tmpl:'今日主力净流入大于{val}亿' },
    { id:'A-大单额', group:'资金', badge:'strong', label:'大单净流入',     type:'num_op',
      ops:['大于'], def_op:'大于', def_val:0.5, unit:'亿', tmpl:'今日大单净流入大于{val}亿' },
    // 技术
    { id:'A-MA5',    group:'技术', badge:'strong', label:'收盘>5日均',    type:'bool', query:'今日收盘价大于5日均线' },
    { id:'A-MA10',   group:'技术', badge:'strong', label:'收盘>10日均',   type:'bool', query:'今日收盘价大于10日均线' },
    { id:'A-MA20',   group:'技术', badge:'strong', label:'收盘>20日均',   type:'bool', query:'今日收盘价大于20日均线' },
    { id:'A-MACD',   group:'技术', badge:'strong', label:'MACD金叉',      type:'bool', query:'MACD金叉' },
    { id:'A-KDJ',    group:'技术', badge:'strong', label:'KDJ金叉',       type:'bool', query:'KDJ金叉' },
    { id:'A-涨停10', group:'技术', badge:'strong', label:'近10日有涨停',  type:'bool', query:'近10日有涨停' },
    // 弱场（yellow 警告）
    { id:'A-成交均', group:'弱场', badge:'weak', label:'成交>5日均×1.5', type:'bool',
      query:'今日成交额大于近5日平均成交额1.5倍' },
    // 禁用（display-only，不可勾选）
    { id:'A-强势股',   group:'禁用', badge:'forbidden', label:'强势股',     type:'forbidden', query:'强势股' },
    { id:'A-放量涨',   group:'禁用', badge:'forbidden', label:'放量上涨',   type:'forbidden', query:'放量上涨股票' },
    { id:'A-龙头',     group:'禁用', badge:'forbidden', label:'短线龙头股', type:'forbidden', query:'短线龙头股' },
    { id:'A-明天涨',   group:'禁用', badge:'forbidden', label:'明天可能上涨', type:'forbidden', query:'明天可能上涨' },
    { id:'A-可涨停',   group:'禁用', badge:'forbidden', label:'有可能涨停', type:'forbidden', query:'有可能涨停' },
  ];

  // ── 板块原子定义 ─────────────────────────────────────────────────────────
  var SECTOR_ATOMS = [
    // 涨跌幅
    { id:'S-今涨',  group:'涨跌幅', badge:'strong', label:'今日涨幅',   type:'num_op',
      ops:['大于','小于'], def_op:'大于', def_val:3,  unit:'%', tmpl:'今日涨幅{op}{val}%' },
    { id:'S-20涨',  group:'涨跌幅', badge:'strong', label:'近20日涨幅', type:'num_op',
      ops:['大于','小于'], def_op:'大于', def_val:0,  unit:'%', tmpl:'近20日涨幅{op}{val}%' },
    { id:'S-60涨',  group:'涨跌幅', badge:'strong', label:'近60日涨幅', type:'num_op',
      ops:['大于','小于'], def_op:'小于', def_val:20, unit:'%', tmpl:'近60日涨幅{op}{val}%' },
    // 排名 TopN
    { id:'S-涨幅排', group:'排名', badge:'strong', label:'涨幅排名前N',    type:'top_n',
      def_n:10, tmpl:'今日涨幅排名前{n}' },
    { id:'S-净流排', group:'排名', badge:'strong', label:'主力净流入排前N', type:'top_n',
      def_n:10, tmpl:'今日主力净流入排名前{n}' },
    { id:'S-成交排', group:'排名', badge:'strong', label:'成交额排名前N',   type:'top_n',
      def_n:10, tmpl:'今日成交额排名前{n}' },
    { id:'S-涨停排', group:'排名', badge:'strong', label:'涨停家数排前N',   type:'top_n',
      def_n:10, tmpl:'今日涨停家数排名前{n}' },
    { id:'S-上涨排', group:'排名', badge:'strong', label:'上涨家数排前N',   type:'top_n',
      def_n:10, tmpl:'今日上涨家数排名前{n}' },
    // 成交/资金
    { id:'S-成交额', group:'成交/资金', badge:'strong', label:'今日成交额',     type:'num_op',
      ops:['大于'], def_op:'大于', def_val:50,  unit:'亿', tmpl:'今日成交额大于{val}亿' },
    { id:'S-主力额', group:'成交/资金', badge:'strong', label:'主力净流入',     type:'num_op',
      ops:['大于'], def_op:'大于', def_val:5,   unit:'亿', tmpl:'今日主力净流入大于{val}亿' },
    { id:'S-主力正', group:'成交/资金', badge:'strong', label:'主力净流入为正', type:'bool',   query:'今日主力净流入为正' },
    { id:'S-换手率', group:'成交/资金', badge:'strong', label:'今日换手率',     type:'num_op',
      ops:['大于'], def_op:'大于', def_val:3,   unit:'%',  tmpl:'今日换手率大于{val}%' },
    { id:'S-量比',   group:'成交/资金', badge:'strong', label:'今日量比',       type:'num_op',
      ops:['大于'], def_op:'大于', def_val:1.2, unit:'',   tmpl:'今日量比大于{val}' },
    // 情绪
    { id:'S-涨停家', group:'情绪', badge:'strong', label:'涨停家数', type:'num_op',
      ops:['大于'], def_op:'大于', def_val:3, unit:'家', tmpl:'今日涨停家数大于{val}' },
    // 禁用（truly_forbidden + semantic_forbidden）
    { id:'S-热门', group:'禁用', badge:'forbidden', label:'热门板块',     type:'forbidden', query:'热门板块' },
    { id:'S-强势', group:'禁用', badge:'forbidden', label:'强势板块',     type:'forbidden', query:'强势板块' },
    { id:'S-最强', group:'禁用', badge:'forbidden', label:'今日最强板块', type:'forbidden', query:'今日最强板块' },
    { id:'S-主线', group:'禁用', badge:'forbidden', label:'主线板块',     type:'forbidden', query:'主线板块',       note:'语义不可信' },
    { id:'S-爆发', group:'禁用', badge:'forbidden', label:'可能爆发',     type:'forbidden', query:'可能爆发的板块', note:'预测性禁词' },
  ];

  // ── 常量 & 全局状态 ──────────────────────────────────────────────────────
  var CANON_FAV_KEY      = 'v6op_canon_favorites';
  var PREVIEW_TIMEOUT_MS = 30000;

  var _mode          = 'astock';
  var _expanded      = false;
  var _linkedSectors = [];

  // 各上下文的原子勾选/参数/阶段
  var _atomChecked = { sector:{}, astock:{}, 'linked-sector':{}, 'linked-astock':{} };
  var _atomParams  = { sector:{}, astock:{}, 'linked-sector':{}, 'linked-astock':{} };
  // IDLE | BUILDING | PREVIEWED | CONFIRMED
  var _stages = { sector:'IDLE', astock:'IDLE', 'linked-sector':'IDLE', 'linked-astock':'IDLE' };

  // ctx → DOM ID 映射
  var _CTX_IDS = {
    sector: {
      atomRows:     'sector-atom-rows',
      queryDisplay: 'sector-atom-query',
      previewBtn:   'btn-sector-preview',
      confirmBtn:   'btn-sector-confirm-source',
      cancelBtn:    'btn-sector-cancel-source',
      clearBtn:     'btn-sector-clear',
      previewResult:'sector-preview-result',
      validation:   'sector-query-validation',
      saveStatus:   'sector-save-status',
    },
    astock: {
      atomRows:     'astock-atom-rows',
      queryDisplay: 'astock-atom-query',
      previewBtn:   'btn-astock-preview',
      confirmBtn:   'btn-astock-confirm-source',
      cancelBtn:    'btn-astock-cancel-source',
      clearBtn:     'btn-astock-clear',
      previewResult:'astock-preview-result',
      validation:   'astock-query-validation',
      saveStatus:   'astock-save-status',
    },
    'linked-sector': {
      atomRows:     'linked-sector-atom-rows',
      queryDisplay: 'linked-sector-atom-query',
      previewBtn:   'btn-linked-sector-preview',
      confirmBtn:   null,
      cancelBtn:    null,
      clearBtn:     'btn-linked-sector-clear',
      previewResult:'linked-sector-result',
      validation:   'linked-sector-validation',
      saveStatus:   null,
    },
    'linked-astock': {
      atomRows:     'linked-astock-atom-rows',
      queryDisplay: 'linked-astock-atom-query',
      previewBtn:   'btn-linked-preview',
      confirmBtn:   'btn-linked-confirm-source',
      cancelBtn:    'btn-linked-cancel-source',
      clearBtn:     'btn-linked-astock-clear',
      previewResult:'linked-preview-result',
      validation:   'linked-astock-validation',
      saveStatus:   'linked-save-status',
    },
  };

  // ── 工具 ─────────────────────────────────────────────────────────────────
  function _esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function _$(id) { return document.getElementById(id); }

  function _showStatus(containerId, msg, type) {
    var el = _$(containerId); if (!el) return;
    var color = type==='ok' ? 'var(--green,#4caf50)' : type==='err' ? 'var(--red,#f44336)' : 'var(--accent,#4a9eff)';
    el.textContent = msg; el.style.color = color; el.classList.remove('hidden');
    if (type==='ok') setTimeout(function(){ el.classList.add('hidden'); }, 4000);
  }

  // ── 原子 → Query 片段 ────────────────────────────────────────────────────
  function _atomToQuery(atom, p) {
    if (atom.type==='forbidden') return null;
    if (atom.type==='bool')      return atom.query;
    p = p || {};
    if (atom.type==='num_op') {
      var op  = (p.op  !== undefined) ? p.op  : atom.def_op;
      var val = (p.val !== undefined) ? p.val : atom.def_val;
      return atom.tmpl.replace('{op}', op).replace('{val}', val);
    }
    if (atom.type==='range') {
      var lo = (p.lo !== undefined) ? p.lo : atom.def_lo;
      var hi = (p.hi !== undefined) ? p.hi : atom.def_hi;
      return atom.tmpl.replace('{lo}', lo).replace('{hi}', hi);
    }
    if (atom.type==='top_n') {
      var n = (p.n !== undefined) ? p.n : atom.def_n;
      return atom.tmpl.replace('{n}', n);
    }
    return null;
  }

  function _ctxAtoms(ctx) {
    return (ctx==='sector' || ctx==='linked-sector') ? SECTOR_ATOMS : ASTOCK_ATOMS;
  }

  function _generateQuery(ctx) {
    var atoms   = _ctxAtoms(ctx);
    var checked = _atomChecked[ctx] || {};
    var params  = _atomParams[ctx]  || {};
    var parts   = [];
    atoms.forEach(function(a) {
      if (!checked[a.id] || a.type==='forbidden') return;
      var q = _atomToQuery(a, params[a.id]);
      if (q) parts.push(q);
    });
    if (!parts.length) return '';
    var joined = parts.join('，');
    return (ctx==='sector' || ctx==='linked-sector') ? joined + '的板块' : joined;
  }

  // ── 状态机 ───────────────────────────────────────────────────────────────
  function _anyChecked(ctx) {
    var chk = _atomChecked[ctx] || {};
    return Object.keys(chk).some(function(k){ return chk[k]; });
  }

  function _setStage(ctx, stage) {
    _stages[ctx] = stage;
    _updateCtxButtons(ctx);
  }

  function _updateCtxButtons(ctx) {
    var ids   = _CTX_IDS[ctx];
    var stage = _stages[ctx];
    var hasAny = _anyChecked(ctx);

    var prevBtn = _$(ids.previewBtn);
    if (prevBtn) prevBtn.disabled = (!hasAny || stage === 'CONFIRMED');

    var confBtn = ids.confirmBtn ? _$(ids.confirmBtn) : null;
    if (confBtn) {
      confBtn.disabled = (stage !== 'PREVIEWED');
      confBtn.style.opacity = (stage === 'PREVIEWED') ? '1' : '0.4';
    }

    var qEl = _$(ids.queryDisplay);
    if (qEl) {
      var q = _generateQuery(ctx);
      qEl.textContent = q || '（未勾选任何条件）';
      qEl.classList.toggle('atom-query-has-content', !!q);
    }
  }

  function _onAtomChange(ctx) {
    var hasAny = _anyChecked(ctx);
    var prev   = _stages[ctx];
    if (!hasAny) {
      _setStage(ctx, 'IDLE');
    } else if (prev === 'IDLE' || prev === 'BUILDING') {
      _setStage(ctx, 'BUILDING');
    } else {
      // Was PREVIEWED/CONFIRMED — atom change invalidates preview
      _setStage(ctx, 'BUILDING');
      _clearPreviewResult(_CTX_IDS[ctx].previewResult);
    }
    // For linked-astock, also refresh the final query display
    if (ctx === 'linked-astock') _updateLinkedFinalQuery();
  }

  // ── 原子 UI 渲染 ─────────────────────────────────────────────────────────
  var _BADGE_CFG = {
    strong:    { cls:'atom-badge-strong',    text:'强' },
    weak:      { cls:'atom-badge-weak',      text:'弱' },
    forbidden: { cls:'atom-badge-forbidden', text:'禁' },
    review:    { cls:'atom-badge-review',    text:'察' },
  };

  function _buildParamsHtml(a) {
    if (a.type==='bool' || a.type==='forbidden') return '';
    var h = '<span class="atom-params hidden">';
    if (a.type==='num_op') {
      if (a.ops && a.ops.length > 1) {
        h += '<select class="atom-param-op">';
        a.ops.forEach(function(op){
          h += '<option'+(op===a.def_op?' selected':'')+'>'+_esc(op)+'</option>';
        });
        h += '</select>';
      } else {
        h += '<span class="atom-op-label">'+_esc(a.def_op)+'</span>';
      }
      h += '<input type="number" class="atom-param-val" value="'+_esc(String(a.def_val))+'" step="0.1" style="width:52px" />';
      if (a.unit) h += '<span class="atom-unit">'+_esc(a.unit)+'</span>';
    } else if (a.type==='range') {
      h += '<input type="number" class="atom-param-lo" value="'+_esc(String(a.def_lo))+'" step="1" style="width:46px" />'
         + '<span class="atom-op-label">–</span>'
         + '<input type="number" class="atom-param-hi" value="'+_esc(String(a.def_hi))+'" step="1" style="width:46px" />'
         + '<span class="atom-unit">'+_esc(a.unit)+'</span>';
    } else if (a.type==='top_n') {
      h += '<span class="atom-op-label">前</span>'
         + '<input type="number" class="atom-param-n" value="'+_esc(String(a.def_n))+'" min="1" max="50" step="1" style="width:42px" />';
    }
    return h + '</span>';
  }

  function _renderAtomGroups(containerId, atoms, ctx) {
    var container = _$(containerId); if (!container) return;
    // Build group order
    var groups = [], groupMap = {};
    atoms.forEach(function(a){
      if (!groupMap[a.group]){ groupMap[a.group]=[]; groups.push(a.group); }
      groupMap[a.group].push(a);
    });
    var html = '';
    groups.forEach(function(g){
      html += '<div class="atom-group"><div class="atom-group-title">'+_esc(g)+'</div>';
      groupMap[g].forEach(function(a){
        var bc = _BADGE_CFG[a.badge] || _BADGE_CFG.strong;
        if (a.type==='forbidden') {
          html += '<div class="atom-row atom-row-forbidden" title="'
               + _esc(a.query||'') + (a.note?' — '+a.note:'') + '">'
               + '<span class="atom-badge '+bc.cls+'">'+bc.text+'</span>'
               + '<span class="atom-label-text atom-label-forbidden">'+_esc(a.label)+'</span>'
               + (a.note ? '<span class="atom-forbidden-note">('+_esc(a.note)+')</span>' : '')
               + '</div>';
        } else {
          var weakNote = a.badge==='weak' ? '<span class="atom-weak-note">弱规律</span>' : '';
          html += '<div class="atom-row" data-atom-id="'+_esc(a.id)+'" data-ctx="'+_esc(ctx)+'">'
               + '<label class="atom-label">'
               + '<input type="checkbox" class="atom-chk" data-atom-id="'+_esc(a.id)+'" data-ctx="'+_esc(ctx)+'" />'
               + '<span class="atom-badge '+bc.cls+'">'+bc.text+'</span>'
               + '<span class="atom-label-text">'+_esc(a.label)+'</span>'
               + '</label>'
               + _buildParamsHtml(a)
               + weakNote
               + '</div>';
        }
      });
      html += '</div>';
    });
    container.innerHTML = html;

    // Bind: checkbox toggles params visibility + triggers state machine
    container.querySelectorAll('.atom-chk').forEach(function(chk){
      chk.addEventListener('change', function(){
        var id = this.dataset.atomId, c = this.dataset.ctx;
        _atomChecked[c] = _atomChecked[c] || {};
        _atomChecked[c][id] = this.checked;
        var row = this.closest('.atom-row');
        if (row) {
          var params = row.querySelector('.atom-params');
          if (params) params.classList.toggle('hidden', !this.checked);
        }
        _onAtomChange(c);
      });
    });

    // Bind: param changes re-generate query
    container.querySelectorAll('.atom-param-op,.atom-param-val,.atom-param-lo,.atom-param-hi,.atom-param-n')
      .forEach(function(inp){
        inp.addEventListener('change', function(){
          var row = this.closest('.atom-row'); if (!row) return;
          var id = row.dataset.atomId, c = row.dataset.ctx;
          _atomParams[c] = _atomParams[c] || {};
          _atomParams[c][id] = _atomParams[c][id] || {};
          if (this.classList.contains('atom-param-op'))  _atomParams[c][id].op  = this.value;
          if (this.classList.contains('atom-param-val')) _atomParams[c][id].val = parseFloat(this.value);
          if (this.classList.contains('atom-param-lo'))  _atomParams[c][id].lo  = parseFloat(this.value);
          if (this.classList.contains('atom-param-hi'))  _atomParams[c][id].hi  = parseFloat(this.value);
          if (this.classList.contains('atom-param-n'))   _atomParams[c][id].n   = parseInt(this.value, 10);
          _updateCtxButtons(c);
          if (c === 'linked-astock') _updateLinkedFinalQuery();
        });
      });
  }

  // ── 清空 / 取消 ──────────────────────────────────────────────────────────
  function _clearConditions(ctx) {
    _atomChecked[ctx] = {};
    _atomParams[ctx]  = {};
    document.querySelectorAll('.atom-chk[data-ctx="'+ctx+'"]').forEach(function(chk){
      chk.checked = false;
      var row = chk.closest('.atom-row');
      if (row){ var p = row.querySelector('.atom-params'); if (p) p.classList.add('hidden'); }
    });
    _clearPreviewResult(_CTX_IDS[ctx].previewResult);
    _setStage(ctx, 'IDLE');
    if (ctx === 'linked-astock') _updateLinkedFinalQuery();
  }

  function _cancelSource(mode) {
    if (mode==='sector') {
      var sq = _$('sector-query'); if (sq){ sq.value=''; sq.dispatchEvent(new Event('input')); }
    } else {
      var wq = _$('wencai-query'); if (wq){ wq.value=''; wq.dispatchEvent(new Event('input')); }
    }
    var banner = _$('canon-confirm-banner'); if (banner) banner.classList.add('hidden');
    var ctx = (mode==='linked') ? 'linked-astock' : mode;
    _setStage(ctx, 'PREVIEWED');
  }

  // ── 初始化 ───────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function(){
    _renderAtomGroups('sector-atom-rows',        SECTOR_ATOMS, 'sector');
    _renderAtomGroups('astock-atom-rows',        ASTOCK_ATOMS, 'astock');
    _renderAtomGroups('linked-sector-atom-rows', SECTOR_ATOMS, 'linked-sector');
    _renderAtomGroups('linked-astock-atom-rows', ASTOCK_ATOMS, 'linked-astock');

    _renderFavorites();
    _bindModeButtons();
    _bindExpandButton();
    _bindSectorPreview();
    _bindAstockPreview();
    _bindLinkedFlow();
    _bindConfirmButtons();
    _bindCancelButtons();
    _bindClearButtons();
    _bindSaveButtons();
    _bindFavLoadButtons();
    _switchMode(_mode);

    ['sector','astock','linked-sector','linked-astock'].forEach(function(ctx){
      _updateCtxButtons(ctx);
    });

    setTimeout(function(){
      var r = document.querySelector('input[name="source-type"][value="wencai"]');
      if (r && !r.checked){ r.checked=true; r.dispatchEvent(new Event('change')); }
      if (typeof setWencaiMode==='function') setWencaiMode('stock', true);
    }, 80);
  });

  // ── 模式切换 ─────────────────────────────────────────────────────────────
  function _switchMode(mode) {
    _mode = mode;
    ['sector','astock','linked'].forEach(function(m){
      var btn   = _$('canon-mode-'+m);
      var panel = _$('canon-panel-'+m);
      if (btn)   btn.classList.toggle('active', m===mode);
      if (panel) panel.classList.toggle('hidden', m!==mode);
    });
    _clearPreviewResult('sector-preview-result');
    _clearPreviewResult('astock-preview-result');
    _clearPreviewResult('linked-sector-result');
    _clearPreviewResult('linked-preview-result');
  }

  function _bindModeButtons(){
    ['sector','astock','linked'].forEach(function(m){
      var btn = _$('canon-mode-'+m);
      if (btn) btn.addEventListener('click', function(){ _switchMode(m); });
    });
  }

  function _bindExpandButton(){
    var btn = _$('canon-expand-btn'); if (!btn) return;
    btn.addEventListener('click', function(){
      _expanded = !_expanded;
      var left = _$('canon-left-panel');
      if (left){
        left.classList.toggle('canon-panel-expanded', _expanded);
        left.classList.toggle('canon-panel-normal', !_expanded);
      }
      btn.textContent = _expanded ? '⟵ 缩回' : '⟷ 放大';
    });
  }

  // ── fetch with timeout ────────────────────────────────────────────────────
  async function _fetchWithTimeout(url, opts, timeoutMs) {
    var controller = new AbortController();
    var tid = setTimeout(function(){ controller.abort(); }, timeoutMs);
    try {
      var resp = await fetch(url, Object.assign({}, opts, { signal: controller.signal }));
      clearTimeout(tid); return resp;
    } catch(e) {
      clearTimeout(tid);
      if (e.name==='AbortError'){
        var err = new Error('接口超过 '+(timeoutMs/1000)+'s 无响应，可能卡住或网络异常');
        err.isTimeout = true; throw err;
      }
      throw e;
    }
  }

  // ── 板块预查 ─────────────────────────────────────────────────────────────
  function _bindSectorPreview(){
    var btn = _$('btn-sector-preview');
    if (btn) btn.addEventListener('click', function(){ _runSectorPreview('sector'); });
  }

  async function _runSectorPreview(ctx) {
    var ids    = _CTX_IDS[ctx];
    var topNEl = (ctx==='sector') ? _$('sector-top-n-canon') : _$('linked-sector-top-n');
    var topN   = parseInt((topNEl||{}).value||'10', 10);
    var query  = _generateQuery(ctx);
    var btn    = _$(ids.previewBtn);
    if (!query){
      _showStatus(ids.saveStatus||'sector-save-status','✖ 请勾选至少一个条件','err'); return;
    }
    _setPreviewLoading(ids.previewResult, true, query, btn);
    var t0 = Date.now();
    try {
      var res  = await _fetchWithTimeout('/api/scan_sectors',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ sector_query:query, sector_top_n:topN }),
      }, PREVIEW_TIMEOUT_MS);
      var data = await res.json();
      if (ctx==='linked-sector'){
        _renderLinkedSectorResult(data, query, Date.now()-t0);
      } else {
        _renderSectorPreviewResult(ids.previewResult, data, query, Date.now()-t0);
      }
      _setStage(ctx, 'PREVIEWED');
    } catch(e){
      _renderPreviewError(ids.previewResult, e.isTimeout?e.message:'网络请求失败: '+e.message, Date.now()-t0);
      _setStage(ctx, 'PREVIEWED');
    } finally { _enableBtn(btn); }
  }

  function _renderSectorPreviewResult(containerId, data, query, elapsedMs){
    var el = _$(containerId); if (!el) return;
    var timeStr  = '<span class="canon-elapsed">耗时 '+(elapsedMs/1000).toFixed(2)+'s</span>';
    var queryStr = '<div class="canon-preview-query">Query：'+_esc(query.slice(0,80))+'</div>';
    if (data.error || !data.sectors || !data.sectors.length){
      el.innerHTML = queryStr+timeStr+'<div class="canon-preview-error">❌ '+_esc(data.error||'返回空结果，请尝试放宽条件')+'</div>';
      el.classList.remove('hidden'); return;
    }
    var sectors = data.sectors||[];
    el.innerHTML = queryStr+timeStr
      +'<div class="canon-preview-header">✓ 返回 <strong>'+sectors.length+'</strong> 个板块</div>'
      +'<div class="canon-sector-chips">'
      +sectors.slice(0,20).map(function(s){ return '<span class="canon-sector-chip">'+_esc(s)+'</span>'; }).join('')
      +'</div>';
    el.classList.remove('hidden');
  }

  // ── A股预查 ──────────────────────────────────────────────────────────────
  function _bindAstockPreview(){
    var btn = _$('btn-astock-preview');
    if (btn) btn.addEventListener('click', function(){ _runAstockPreview('astock'); });
  }

  async function _runAstockPreview(ctx) {
    var ids   = _CTX_IDS[ctx];
    var query = _generateQuery(ctx);
    var btn   = _$(ids.previewBtn);
    if (!query){
      _showStatus(ids.saveStatus||'astock-save-status','✖ 请勾选至少一个条件','err'); return;
    }
    _setPreviewLoading(ids.previewResult, true, query, btn);
    var t0 = Date.now();
    try {
      var res  = await _fetchWithTimeout('/api/wencai/preview',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ query:query, limit:20 }),
      }, PREVIEW_TIMEOUT_MS);
      var data = await res.json();
      _renderAstockPreviewResult(ids.previewResult, data, query, Date.now()-t0);
      _setStage(ctx, 'PREVIEWED');
    } catch(e){
      _renderPreviewError(ids.previewResult, e.isTimeout?e.message:'网络请求失败: '+e.message, Date.now()-t0);
      _setStage(ctx, 'PREVIEWED');
    } finally { _enableBtn(btn); }
  }

  function _renderAstockPreviewResult(containerId, data, query, elapsedMs){
    var el = _$(containerId); if (!el) return;
    var status   = data.status||'unknown';
    var timeStr  = '<span class="canon-elapsed">耗时 '+(elapsedMs/1000).toFixed(2)+'s</span>';
    var queryStr = '<div class="canon-preview-query">Query：'+_esc((query||data.query||'').slice(0,80))+'</div>';
    if (status!=='ok'){
      var reason = data.error||data.note||('接口状态: '+status);
      var hint   = _getWencaiHint(status, reason);
      el.innerHTML = queryStr+timeStr
        +'<div class="canon-preview-error">❌ 试跑受阻 ['+_esc(status)+']<br>'
        +'<span class="canon-preview-reason">'+_esc(reason)+'</span>'
        +(hint?'<br><span class="canon-preview-hint">'+_esc(hint)+'</span>':'')
        +'</div>';
      el.classList.remove('hidden'); return;
    }
    var codes = data.codes||[];
    el.innerHTML = queryStr+timeStr
      +'<div class="canon-preview-header">✓ 返回 <strong>'+data.count+'</strong> 只（显示前 '+codes.length+' 只）</div>'
      +'<div class="canon-code-chips">'
      +codes.map(function(c){ return '<span class="canon-code-chip">'+_esc(c)+'</span>'; }).join('')
      +'</div>';
    el.classList.remove('hidden');
  }

  function _getWencaiHint(status, note){
    if (note && (note.includes('pywencai')||note.includes('未安装'))) return '请执行: pip install pywencai';
    var hints = {
      key_missing: '请安装 pywencai 并配置 cookie：pip install pywencai',
      blocked:     '问财触发风控，等待 5~10 分钟后重试，或检查 cookie',
      auth_failed: 'cookie/token 过期，重新登录问财获取 cookie',
      network_error:'网络不可达，检查代理/VPN',
      empty_result: '条件过严，返回空股票列表，请适当放宽',
      api_error:    '问财接口内部错误，检查 query 语法，参考法典禁用词',
    };
    return hints[status]||'';
  }

  // ── 联动模式 ─────────────────────────────────────────────────────────────
  function _bindLinkedFlow(){
    var btnScan = _$('btn-linked-sector-preview');
    if (btnScan) btnScan.addEventListener('click', function(){ _runSectorPreview('linked-sector'); });
    var btnConfirm = _$('btn-linked-confirm-sectors');
    if (btnConfirm) btnConfirm.addEventListener('click', _confirmLinkedSectors);
    var btnLinked = _$('btn-linked-preview');
    if (btnLinked) btnLinked.addEventListener('click', _runLinkedPreview);
  }

  function _renderLinkedSectorResult(data, query, elapsedMs){
    var el = _$('linked-sector-result'); if (!el) return;
    var timeStr  = '<span class="canon-elapsed">耗时 '+(elapsedMs/1000).toFixed(2)+'s</span>';
    var queryStr = '<div class="canon-preview-query">Query：'+_esc((query||'').slice(0,80))+'</div>';
    if (data.error || !data.sectors || !data.sectors.length){
      el.innerHTML = queryStr+timeStr+'<div class="canon-preview-error">❌ '+_esc(data.error||'返回空')+'</div>';
      el.classList.remove('hidden'); return;
    }
    var sectors = data.sectors||[];
    el.innerHTML = queryStr+timeStr
      +'<div class="canon-preview-header">✓ '+sectors.length+' 个板块，请勾选：</div>'
      +'<div class="canon-sector-checklist">'
      +sectors.map(function(s){
        return '<label class="canon-chk-item">'
          +'<input type="checkbox" class="linked-sector-chk" value="'+_esc(s)+'" checked /> '+_esc(s)
          +'</label>';
      }).join('')
      +'</div>';
    el.classList.remove('hidden');
    var confirmRow = _$('linked-sector-confirm-row');
    if (confirmRow) confirmRow.classList.remove('hidden');
  }

  function _confirmLinkedSectors(){
    var checked = Array.from(document.querySelectorAll('.linked-sector-chk:checked'))
      .map(function(cb){ return cb.value; }).filter(Boolean);
    if (!checked.length){ _renderPreviewError('linked-sector-result','请至少勾选一个板块'); return; }
    _linkedSectors = checked;
    var display = _$('linked-confirmed-sectors');
    if (display){
      display.innerHTML = '<span class="canon-preview-header">已确认板块：</span>'
        + checked.map(function(s){ return '<span class="canon-sector-chip">'+_esc(s)+'</span>'; }).join('');
      display.classList.remove('hidden');
    }
    var phaseB = _$('linked-phase-b-panel'); if (phaseB) phaseB.classList.remove('hidden');
    _updateLinkedFinalQuery();
  }

  function _updateLinkedFinalQuery(){
    var astockCond = _generateQuery('linked-astock');
    var combined   = _buildLinkedQuery(_linkedSectors, astockCond);
    var finalEl    = _$('linked-final-query-preview');
    if (finalEl) finalEl.textContent = combined || '（请先确认板块，再勾选 A股条件）';
  }

  function buildLinkedQuery(sectors, astockCondition){ return _buildLinkedQuery(sectors, astockCondition); }
  window.canonBuildLinkedQuery = buildLinkedQuery;

  function _buildLinkedQuery(sectors, astockCondition){
    if (!sectors||!sectors.length) return '';
    var clause = sectors.map(function(s){ return s+'板块'; }).join('或');
    return '属于'+clause+(astockCondition?'，且'+astockCondition:'');
  }

  async function _runLinkedPreview(){
    if (!_linkedSectors.length){
      _renderPreviewError('linked-preview-result','请先完成 Phase A：试跑板块并勾选确认'); return;
    }
    var astockCond = _generateQuery('linked-astock');
    if (!astockCond){
      _renderPreviewError('linked-preview-result','请勾选 Phase B A股条件（不可为空）'); return;
    }
    var finalQuery = _buildLinkedQuery(_linkedSectors, astockCond);
    var btn = _$('btn-linked-preview');
    _setPreviewLoading('linked-preview-result', true, finalQuery, btn);
    var t0 = Date.now();
    try {
      var res  = await _fetchWithTimeout('/api/wencai/preview',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ query:finalQuery, limit:20 }),
      }, PREVIEW_TIMEOUT_MS);
      var data = await res.json();
      _renderAstockPreviewResult('linked-preview-result', data, finalQuery, Date.now()-t0);
      _setStage('linked-astock', 'PREVIEWED');
    } catch(e){
      _renderPreviewError('linked-preview-result', e.isTimeout?e.message:'网络请求失败: '+e.message, Date.now()-t0);
      _setStage('linked-astock', 'PREVIEWED');
    } finally { _enableBtn(btn); }
  }

  // ── 确认 / 取消 / 清空 绑定 ──────────────────────────────────────────────
  function _bindConfirmButtons(){
    var btnS = _$('btn-sector-confirm-source');
    if (btnS) btnS.addEventListener('click', function(){ _confirmSource('sector'); });
    var btnA = _$('btn-astock-confirm-source');
    if (btnA) btnA.addEventListener('click', function(){ _confirmSource('astock'); });
    var btnL = _$('btn-linked-confirm-source');
    if (btnL) btnL.addEventListener('click', function(){ _confirmSource('linked'); });
  }

  function _bindCancelButtons(){
    var btnS = _$('btn-sector-cancel-source');
    if (btnS) btnS.addEventListener('click', function(){ _cancelSource('sector'); });
    var btnA = _$('btn-astock-cancel-source');
    if (btnA) btnA.addEventListener('click', function(){ _cancelSource('astock'); });
    var btnL = _$('btn-linked-cancel-source');
    if (btnL) btnL.addEventListener('click', function(){ _cancelSource('linked'); });
  }

  function _bindClearButtons(){
    var btnS  = _$('btn-sector-clear');        if (btnS)  btnS.addEventListener('click',  function(){ _clearConditions('sector'); });
    var btnA  = _$('btn-astock-clear');        if (btnA)  btnA.addEventListener('click',  function(){ _clearConditions('astock'); });
    var btnLS = _$('btn-linked-sector-clear'); if (btnLS) btnLS.addEventListener('click', function(){ _clearConditions('linked-sector'); });
    var btnLA = _$('btn-linked-astock-clear'); if (btnLA) btnLA.addEventListener('click', function(){ _clearConditions('linked-astock'); });
  }

  function _confirmSource(mode){
    var finalQuery = '';
    var meta = {};
    var ctx = (mode==='linked') ? 'linked-astock' : mode;
    var statusId = (_CTX_IDS[ctx]||{}).saveStatus;

    if (mode==='sector'){
      finalQuery = _generateQuery('sector');
      if (!finalQuery){ _showStatus(statusId,'✖ 板块查询语句为空，无法确认','err'); return; }
      var sq = _$('sector-query');
      if (sq){ sq.value=finalQuery; sq.dispatchEvent(new Event('input')); }
      var topN = _$('sector-top-n-canon'), topNSink = _$('sector-top-n');
      if (topN&&topNSink) topNSink.value=topN.value;
      var r = document.querySelector('input[name="source-type"][value="wencai"]');
      if (r){ r.checked=true; r.dispatchEvent(new Event('change')); }
      if (typeof setWencaiMode==='function') setWencaiMode('sector', false);
      meta = { mode:'sector', query:finalQuery };
      _setStage('sector', 'CONFIRMED');

    } else if (mode==='astock'){
      finalQuery = _generateQuery('astock');
      if (!finalQuery){ _showStatus(statusId,'✖ A股查询语句为空，无法确认','err'); return; }
      var wq = _$('wencai-query');
      if (wq){ wq.value=finalQuery; wq.dispatchEvent(new Event('input')); }
      var rA = document.querySelector('input[name="source-type"][value="wencai"]');
      if (rA){ rA.checked=true; rA.dispatchEvent(new Event('change')); }
      if (typeof setWencaiMode==='function') setWencaiMode('stock', false);
      meta = { mode:'astock', query:finalQuery };
      _setStage('astock', 'CONFIRMED');

    } else if (mode==='linked'){
      if (!_linkedSectors.length){ _showStatus(statusId,'✖ 请先完成 Phase A：确认板块','err'); return; }
      var aCond = _generateQuery('linked-astock');
      finalQuery = _buildLinkedQuery(_linkedSectors, aCond);
      if (!finalQuery){ _showStatus(statusId,'✖ 联动 query 生成失败','err'); return; }
      var wqL = _$('wencai-query');
      if (wqL){ wqL.value=finalQuery; wqL.dispatchEvent(new Event('input')); }
      var rL = document.querySelector('input[name="source-type"][value="wencai"]');
      if (rL){ rL.checked=true; rL.dispatchEvent(new Event('change')); }
      if (typeof setWencaiMode==='function') setWencaiMode('stock', false);
      meta = { mode:'linked', confirmed_sectors:_linkedSectors.slice(), final_query:finalQuery };
      _setStage('linked-astock', 'CONFIRMED');
    }

    if (typeof notifyStrategyStateChanged==='function') notifyStrategyStateChanged();
    document.dispatchEvent(new Event('v6op:strategy-state-change'));
    _showConfirmBanner(finalQuery, meta);
    window._canonLastMeta = meta;
  }

  function _showConfirmBanner(query, meta){
    var banner = _$('canon-confirm-banner'); if (!banner) return;
    var label = {sector:'板块',astock:'A股',linked:'联动'}[meta.mode]||meta.mode;
    banner.innerHTML = '<span class="canon-confirm-ok">✔ 已确认为来源</span>'
      +' ['+label+'] — '+_esc(query.length>60?query.slice(0,60)+'…':query);
    banner.classList.remove('hidden');
    var previewSrc = _$('preview-source');
    if (previewSrc){
      previewSrc.style.borderColor='var(--green,#4caf50)';
      setTimeout(function(){ previewSrc.style.borderColor=''; }, 3000);
    }
  }

  // ── 收藏 ─────────────────────────────────────────────────────────────────
  function _bindSaveButtons(){
    var btnS = _$('btn-save-sector-canon');  if (btnS) btnS.addEventListener('click', function(){ _saveFavorite('sector'); });
    var btnA = _$('btn-save-astock-canon');  if (btnA) btnA.addEventListener('click', function(){ _saveFavorite('astock'); });
    var btnL = _$('btn-save-linked-canon');  if (btnL) btnL.addEventListener('click', function(){ _saveFavorite('linked'); });
  }

  function _saveFavorite(type){
    var query='', statusId=type+'-save-status';
    if (type==='sector')      query = _generateQuery('sector');
    else if (type==='astock') query = _generateQuery('astock');
    else if (type==='linked') query = _buildLinkedQuery(_linkedSectors, _generateQuery('linked-astock'));
    if (!query){ _showStatus(statusId,'✖ 查询为空，无法收藏','err'); return; }
    var label = query.length>22 ? query.slice(0,22)+'…' : query;
    var favs   = _loadFavorites();
    var prefix = type==='sector' ? 'SECTOR' : type==='astock' ? 'ASTOCK' : 'LINK';
    var num    = String(favs.filter(function(f){ return f.type===type; }).length+1).padStart(3,'0');
    favs.unshift({
      id:prefix+'-'+num, type:type, label:label, query:query,
      confirmed_sectors: type==='linked' ? _linkedSectors.slice() : undefined,
      saved_at: new Date().toISOString().slice(0,16), use_count:0,
    });
    if (favs.length>50) favs.pop();
    _storeFavorites(favs); _renderFavorites();
    _showStatus(statusId,'✔ 已保存为 '+prefix+'-'+num,'ok');
  }

  function _loadFavorites(){ try{ return JSON.parse(localStorage.getItem(CANON_FAV_KEY)||'[]'); }catch(_){ return []; } }
  function _storeFavorites(favs){ try{ localStorage.setItem(CANON_FAV_KEY, JSON.stringify(favs)); }catch(_){} }

  function _renderFavorites(){
    ['sector','astock','linked'].forEach(function(type){
      var el = _$('canon-fav-list-'+type); if (!el) return;
      var favs = _loadFavorites().filter(function(f){ return f.type===type; });
      if (!favs.length){ el.innerHTML='<span class="text-muted" style="font-size:11px">暂无收藏</span>'; return; }
      el.innerHTML = favs.map(function(f,i){
        return '<div class="canon-fav-item" data-idx="'+i+'" data-type="'+_esc(type)+'">'
          +'<span class="canon-fav-id">'+_esc(f.id)+'</span>'
          +'<span class="canon-fav-label" title="'+_esc(f.query)+'">'+_esc(f.label)+'</span>'
          +'<span class="canon-fav-count">×'+(f.use_count||0)+'</span>'
          +'<button class="canon-fav-load" type="button">填入</button>'
          +'<button class="canon-fav-del" type="button">✕</button>'
          +'</div>';
      }).join('');
      el.querySelectorAll('.canon-fav-load').forEach(function(btn){
        btn.addEventListener('click', function(){
          _loadFavoriteByTypeIdx(type, parseInt(this.closest('.canon-fav-item').dataset.idx,10));
        });
      });
      el.querySelectorAll('.canon-fav-del').forEach(function(btn){
        btn.addEventListener('click', function(){
          _deleteFavoriteByTypeIdx(type, parseInt(this.closest('.canon-fav-item').dataset.idx,10));
        });
      });
    });
  }

  function _bindFavLoadButtons(){
    ['sector','astock','linked'].forEach(function(type){
      var tab = _$('canon-fav-tab-'+type); if (!tab) return;
      tab.addEventListener('click', function(){
        ['sector','astock','linked'].forEach(function(t){
          var t2=_$('canon-fav-tab-'+t), p2=_$('canon-fav-list-'+t);
          if (t2) t2.classList.toggle('active', t===type);
          if (p2) p2.classList.toggle('hidden', t!==type);
        });
      });
    });
  }

  function _loadFavoriteByTypeIdx(type, idx){
    var favs = _loadFavorites().filter(function(f){ return f.type===type; });
    var fav  = favs[idx]; if (!fav) return;
    _switchMode(type==='linked'?'linked':type);
    if (type==='linked' && fav.confirmed_sectors && fav.confirmed_sectors.length){
      _linkedSectors = fav.confirmed_sectors.slice();
      var disp = _$('linked-confirmed-sectors');
      if (disp){
        disp.innerHTML = '<span class="canon-preview-header">已确认板块（从收藏恢复）：</span>'
          + _linkedSectors.map(function(s){ return '<span class="canon-sector-chip">'+_esc(s)+'</span>'; }).join('');
        disp.classList.remove('hidden');
      }
      var phaseB = _$('linked-phase-b-panel'); if (phaseB) phaseB.classList.remove('hidden');
      _updateLinkedFinalQuery();
    }
    var statusId = (_CTX_IDS[type==='linked'?'linked-astock':type]||{}).saveStatus;
    _showStatus(statusId||'astock-save-status','已加载收藏（请手动匹配条件后重新预查）','info');
    var allFavs = _loadFavorites();
    var allIdx  = allFavs.findIndex(function(f){ return f.type===type&&f.id===fav.id; });
    if (allIdx!==-1){ allFavs[allIdx].use_count=(allFavs[allIdx].use_count||0)+1; _storeFavorites(allFavs); }
  }

  function _deleteFavoriteByTypeIdx(type, idx){
    var favs   = _loadFavorites();
    var target = favs.filter(function(f){ return f.type===type; })[idx]; if (!target) return;
    _storeFavorites(favs.filter(function(f){ return !(f.type===type&&f.id===target.id); }));
    _renderFavorites();
  }

  // ── UI helpers ────────────────────────────────────────────────────────────
  function _setPreviewLoading(containerId, loading, query, btn){
    var el = _$(containerId); if (!el) return;
    if (loading){
      var qPrev = query ? '<div class="canon-preview-query">Query：'+_esc(query.slice(0,60))+(query.length>60?'…':'')+'</div>' : '';
      el.innerHTML = qPrev+'<span class="spinner"></span> 预查中，最多等待 30s…';
      el.classList.remove('hidden');
      if (btn) btn.disabled = true;
    }
  }
  function _enableBtn(btn){ if (btn) btn.disabled=false; }
  function _clearPreviewResult(containerId){
    var el = _$(containerId); if (el){ el.innerHTML=''; el.classList.add('hidden'); }
  }
  function _renderPreviewError(containerId, msg, elapsedMs){
    var el = _$(containerId); if (!el) return;
    var timeStr = (elapsedMs!==undefined)?'<span class="canon-elapsed"> 耗时 '+(elapsedMs/1000).toFixed(2)+'s</span>':'';
    el.innerHTML = '<div class="canon-preview-error">❌ '+_esc(msg)+timeStr+'</div>';
    el.classList.remove('hidden');
  }

})();
