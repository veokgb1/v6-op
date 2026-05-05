/* V6OP 操盘台 — app.js */
'use strict';

// ── 常量 ──────────────────────────────────────────────────────────────
const API = {
  health: '/api/health',
  run:    '/api/run',
  result: '/api/result',
  stream: '/api/stream',
};

const SKILL_META = {
  czsc:     { label: '缠论买点',  note: '一买/二买/三买买点检测，仅读本地缓存', semantics: 'positive' },
  smc:      { label: 'SMC 聪明钱', note: 'BOS/ChoCH/FVG 聪明钱信号，仅读本地缓存', semantics: 'positive' },
  kline:    { label: 'K线形态',   note: '15种形态分析（锤子/吞没/启明星等），纯本地', semantics: 'positive' },
  wave:     { label: '波浪分析',  note: '弱信号/辅助参考，Elliott Wave + Zigzag', semantics: 'positive', isWeak: true },
  landmine: { label: '排雷过滤',  note: '负向过滤：北交所/ST/K线不足/缓存缺失', semantics: 'negative' },
};

// 灰色技能列表由 /api/skill_catalog 动态装载（来源：V6 JSON）。
// 不在此处手写；见 scripts/skill_catalog.py。
let SKILL_CATALOG_GRAY = [];

// 每个技能的可调参数，默认值对齐 skill_registry.py
const SKILL_PARAMS = {
  czsc: [
    { name: 'signal_bars', label: '买点窗口', hint: '近 N 根 K 线内有买点才保留', type: 'int',   default: 5 },
    { name: 'buy_type',    label: '买点类型', hint: '一买/二买/三买 或全部',       type: 'select',
      options: [{v:'all',l:'全部'},{v:'1st',l:'一买'},{v:'2nd',l:'二买'},{v:'3rd',l:'三买'}],
      default: 'all' },
    { name: 'days',        label: '回看天数', hint: '加载最近 N 天 K 线',           type: 'int',   default: 365 },
  ],
  smc: [
    { name: 'signal_bars', label: '信号窗口', hint: '近 N 根内有 BOS/ChoCH/FVG 才保留', type: 'int', default: 15 },
    { name: 'swing_length', label: '摆动窗口', hint: '识别结构高低点的观察范围', type: 'int', default: 10 },
    { name: 'close_break', label: '收盘突破', hint: '是：要求收盘价确认突破；否：放宽确认', type: 'bool', default: true },
    { name: 'mode',        label: '分析模式', hint: 'strict=正式路径  soft_filter=调试透传',
      type: 'select',
      options: [
        {v:'strict',     l:'strict（正式路径）'},
        {v:'soft_filter',l:'soft_filter（调试/透传）— 标注为软过滤'},
        {v:'bypass',     l:'bypass（透传所有）'},
      ],
      default: 'strict' },
    { name: 'days', label: '回看天数', hint: '加载最近 N 天 K 线', type: 'int', default: 365 },
  ],
  kline: [
    { name: 'signal_bars',  label: '形态窗口', hint: '近 N 根内有形态才保留',     type: 'int',   default: 5 },
    { name: 'body_pct',     label: '实体阈值', hint: '十字星：实体/振幅比例下限', type: 'float', default: 0.1 },
    { name: 'shadow_ratio', label: '影线倍数', hint: '影线 ÷ 实体长度阈值',        type: 'float', default: 2.0 },
    { name: 'pass_neutral', label: '中性放行', hint: '是：中性形态也可通过；否：必须有正向形态', type: 'bool', default: false },
    { name: 'days',         label: '回看天数', hint: '加载最近 N 天 K 线',         type: 'int',   default: 365 },
  ],
  wave: [
    { name: 'signal_bars', label: '波浪窗口', hint: '近 N 根内有波浪结构才保留', type: 'int', default: 20 },
    { name: 'swing_window', label: '拐点窗口', hint: '识别波峰波谷的观察范围', type: 'int', default: 10 },
    { name: 'fib_tolerance', label: '比例容差', hint: 'Fibonacci 比例允许偏差', type: 'float', default: 0.15 },
    { name: 'days',        label: '回看天数', hint: '加载最近 N 天 K 线',       type: 'int', default: 365 },
  ],
  landmine: [],
};

// ── 状态 ──────────────────────────────────────────────────────────────
let _pollTimer = null;
let _lastResult = null;
let _lastEventCount = 0;   // 游标：已收到的事件总数（对齐 server.event_count）

// ── DOM 引用 ──────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

// 已接通技能 skill_id 集合，用于 buildStrategy() 双重防守
const LIVE_SKILL_IDS = new Set(Object.keys(SKILL_META));

// ── 参数持久化（总纲第十一章）────────────────────────────────────────
const PARAMS_STORE_ID = 'v6op_last_params';

function saveParams() {
  try {
    const sourceType = document.querySelector('input[name="source-type"]:checked')?.value || 'manual';
    const pathType   = document.querySelector('input[name="path-type"]:checked')?.value || 'parallel_and';
    const skills = [];
    document.querySelectorAll('#skill-list input[type=checkbox][data-live="true"]:checked').forEach(cb => {
      skills.push(cb.value);
    });
    const skillParams = {};
    for (const id of Object.keys(SKILL_META)) {
      const defs = SKILL_PARAMS[id] || [];
      if (defs.length === 0) continue;
      const sp = {};
      for (const pd of defs) {
        const el = document.getElementById(`p-${id}-${pd.name}`);
        if (el) sp[pd.name] = el.value;
      }
      if (Object.keys(sp).length > 0) skillParams[id] = sp;
    }
    const wencaiQuery  = document.getElementById('wencai-query')?.value || '';
    const wencaiLimit  = document.getElementById('wencai-limit')?.value || '50';
    const manualCodes  = document.getElementById('manual-codes')?.value || '';

    const saved = { sourceType, pathType, skills, skillParams, wencaiQuery, wencaiLimit, manualCodes };
    localStorage.setItem(PARAMS_STORE_ID, JSON.stringify(saved));
  } catch (_) {}
}

function restoreParams() {
  try {
    const raw = localStorage.getItem(PARAMS_STORE_ID);
    if (!raw) return;
    const saved = JSON.parse(raw);

    // 来源类型
    const srcRadio = document.querySelector(`input[name="source-type"][value="${saved.sourceType}"]`);
    if (srcRadio) { srcRadio.checked = true; srcRadio.dispatchEvent(new Event('change')); }

    // 路径类型
    const pathRadio = document.querySelector(`input[name="path-type"][value="${saved.pathType}"]`);
    if (pathRadio) pathRadio.checked = true;

    // 技能勾选
    const skillSet = new Set(saved.skills || []);
    document.querySelectorAll('#skill-list input[type=checkbox][data-live="true"]').forEach(cb => {
      const checked = skillSet.has(cb.value);
      if (cb.checked !== checked) {
        cb.checked = checked;
        cb.dispatchEvent(new Event('change'));
      }
    });

    // skill 参数值
    if (saved.skillParams) {
      for (const [id, sp] of Object.entries(saved.skillParams)) {
        for (const [name, val] of Object.entries(sp)) {
          const el = document.getElementById(`p-${id}-${name}`);
          if (el) el.value = val;
        }
      }
    }

    // wencai / manual 输入
    const wq = document.getElementById('wencai-query');
    if (wq && saved.wencaiQuery) wq.value = saved.wencaiQuery;
    const wl = document.getElementById('wencai-limit');
    if (wl && saved.wencaiLimit) wl.value = saved.wencaiLimit;
    const mc = document.getElementById('manual-codes');
    if (mc && saved.manualCodes) mc.value = saved.manualCodes;
  } catch (_) {}
}

function resetParams() {
  try { localStorage.removeItem(PARAMS_STORE_ID); } catch (_) {}
  // 恢复 SKILL_META 默认值
  const defaults = new Set(['kline', 'landmine']);
  document.querySelectorAll('#skill-list input[type=checkbox][data-live="true"]').forEach(cb => {
    const checked = defaults.has(cb.value);
    if (cb.checked !== checked) {
      cb.checked = checked;
      cb.dispatchEvent(new Event('change'));
    }
  });
  for (const [id, defs] of Object.entries(SKILL_PARAMS)) {
    for (const pd of defs) {
      const el = document.getElementById(`p-${id}-${pd.name}`);
      if (!el) continue;
      el.value = String(pd.default);
    }
  }
  const srcRadio = document.querySelector('input[name="source-type"][value="manual"]');
  if (srcRadio) { srcRadio.checked = true; srcRadio.dispatchEvent(new Event('change')); }
  const pathRadio = document.querySelector('input[name="path-type"][value="parallel_and"]');
  if (pathRadio) pathRadio.checked = true;
  const wq = document.getElementById('wencai-query');
  if (wq) wq.value = '';
  const mc = document.getElementById('manual-codes');
  if (mc) mc.value = '';
}

// ── 初始化 ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  // 从 /api/skill_catalog 装载 V6 JSON 灰卡（总纲第四章）
  try {
    const res = await fetch('/api/skill_catalog');
    if (res.ok) {
      const cat = await res.json();
      SKILL_CATALOG_GRAY = cat.gray || [];
    }
  } catch (_) { /* 无服务器时回退到空列表 */ }

  buildSkillList();
  bindSourceToggle();
  bindAllALimitWatch();
  restoreParams();   // 回显上次参数（总纲第十一章）
  bindResetParams();
  checkHealth();
});

// ── 健康检查 ──────────────────────────────────────────────────────────
async function checkHealth() {
  const dot   = $('health-dot');
  const label = $('health-label');
  try {
    const res  = await fetch(API.health);
    const data = await res.json();
    const ok   = data.status === 'ok';
    dot.className   = 'health-dot ' + (ok ? 'ok' : 'err');
    label.textContent = ok
      ? `后端就绪  Python ${data.python_version.split(' ')[0]}`
      : `后端异常: ${data.status}`;
    const envVars = (data.dot_env_var_names || []).join(', ');
    if (envVars) label.textContent += `  |  .env 变量名: ${envVars}`;
  } catch {
    dot.className = 'health-dot err';
    label.textContent = '后端不可达，请先启动: python scripts/v6op_server.py';
  }
}

// ── 技能列表构建（含参数面板）────────────────────────────────────────
function buildSkillList() {
  const container = $('skill-list');
  container.innerHTML = '';
  const defaults = new Set(['kline', 'landmine']);

  // ── 已接通技能（绿色可用）──────────────────────────────────────────
  for (const [id, meta] of Object.entries(SKILL_META)) {
    const item = document.createElement('div');
    item.className = 'skill-item';

    const row = document.createElement('div');
    row.className = 'skill-label';

    const cb = document.createElement('input');
    cb.type    = 'checkbox';
    cb.id      = `skill-${id}`;
    cb.value   = id;
    cb.checked = defaults.has(id);
    cb.dataset.live = 'true';

    const lbl = document.createElement('label');
    lbl.htmlFor     = cb.id;
    lbl.textContent = meta.label;

    if (meta.isWeak) {
      const t = document.createElement('span');
      t.className = 'tag tag-weak';
      t.textContent = '弱信号';
      lbl.appendChild(document.createTextNode(' '));
      lbl.appendChild(t);
    }
    if (meta.semantics === 'negative') {
      const t = document.createElement('span');
      t.className = 'tag tag-neg';
      t.textContent = '负向';
      lbl.appendChild(document.createTextNode(' '));
      lbl.appendChild(t);
    }

    row.appendChild(cb);
    row.appendChild(lbl);
    item.appendChild(row);

    const note = document.createElement('div');
    note.className   = 'skill-note';
    note.textContent = meta.note;
    item.appendChild(note);

    const paramDefs = SKILL_PARAMS[id] || [];
    if (paramDefs.length > 0) {
      const panel = document.createElement('div');
      panel.className = 'skill-params';
      panel.id        = `params-${id}`;
      panel.style.cssText = 'padding-left:20px;margin-top:5px;display:flex;flex-direction:column;gap:4px;';

      for (const pd of paramDefs) {
        const prow = document.createElement('div');
        prow.style.cssText = 'display:flex;align-items:center;gap:6px;flex-wrap:wrap;';

        const pl = document.createElement('label');
        pl.htmlFor    = `p-${id}-${pd.name}`;
        pl.textContent = pd.label;
        pl.style.cssText = 'color:var(--label);font-size:11px;min-width:58px;flex-shrink:0;';

        let inp;
        if (pd.type === 'select' || pd.type === 'bool') {
          inp = document.createElement('select');
          inp.style.cssText = 'width:auto;padding:3px 6px;font-size:11px;';
          const options = pd.type === 'bool'
            ? [{v:'true', l:'是'}, {v:'false', l:'否'}]
            : pd.options;
          for (const opt of options) {
            const o = document.createElement('option');
            o.value       = opt.v;
            o.textContent = opt.l;
            if (String(opt.v) === String(pd.default)) o.selected = true;
            inp.appendChild(o);
          }
          if (id === 'smc' && pd.name === 'mode') {
            const modeWarn = document.createElement('span');
            modeWarn.id = 'smc-mode-warn';
            modeWarn.style.display = 'none';
            modeWarn.innerHTML = '<span class="tag tag-debug">调试/软过滤</span>';
            inp.addEventListener('change', () => {
              modeWarn.style.display = (inp.value !== 'strict') ? 'inline' : 'none';
            });
            prow.appendChild(pl);
            prow.appendChild(inp);
            prow.appendChild(modeWarn);
            inp.id = `p-${id}-${pd.name}`;
            panel.appendChild(prow);
            continue;
          }
        } else {
          inp = document.createElement('input');
          inp.type  = pd.type === 'int' ? 'number' : 'number';
          inp.step  = pd.type === 'int' ? '1' : '0.01';
          inp.value = String(pd.default);
          inp.style.cssText = 'width:72px;font-size:11px;padding:3px 6px;';
        }
        inp.id = `p-${id}-${pd.name}`;

        const hint = document.createElement('span');
        hint.textContent = pd.hint;
        hint.style.cssText = 'font-size:10px;color:var(--muted);';

        prow.appendChild(pl);
        prow.appendChild(inp);
        prow.appendChild(hint);
        panel.appendChild(prow);
      }

      panel.style.display = cb.checked ? 'flex' : 'none';
      cb.addEventListener('change', () => {
        panel.style.display = cb.checked ? 'flex' : 'none';
      });

      item.appendChild(panel);
    }

    container.appendChild(item);
  }

  // ── 未接通技能（灰色，不可勾选）─────────────────────────────────────
  const sep = document.createElement('div');
  sep.style.cssText = 'margin-top:10px;padding-top:6px;border-top:1px solid var(--border);'
    + 'font-size:10px;color:var(--muted);letter-spacing:.5px;';
  sep.textContent = '── V6 技能资产（暂未接通）──';
  container.appendChild(sep);

  for (const gs of SKILL_CATALOG_GRAY) {
    const item = document.createElement('div');
    item.className = 'skill-item skill-item-gray';
    item.style.cssText = 'opacity:.55;';
    item.dataset.graySkillId = gs.skill_id;

    const row = document.createElement('div');
    row.className = 'skill-label';

    const cb = document.createElement('input');
    cb.type     = 'checkbox';
    cb.id       = `skill-gray-${gs.skill_id}`;
    cb.value    = gs.skill_id;
    cb.disabled = true;
    cb.dataset.gray = 'true';

    const lbl = document.createElement('label');
    lbl.htmlFor     = cb.id;
    lbl.textContent = gs.label;
    lbl.style.color = 'var(--muted)';

    const tag = document.createElement('span');
    tag.className   = 'tag';
    tag.style.cssText = 'background:#2a2a2a;color:#888;margin-left:4px;font-size:9px;';
    tag.textContent = gs.statusCn;

    row.appendChild(cb);
    row.appendChild(lbl);
    row.appendChild(tag);
    item.appendChild(row);

    const note = document.createElement('div');
    note.className   = 'skill-note';
    note.style.color = 'var(--muted)';
    note.textContent = `暂未接通  (${gs.skill_id})`;
    item.appendChild(note);

    container.appendChild(item);
  }
}

// ── 来源切换 ──────────────────────────────────────────────────────────
function bindSourceToggle() {
  const radios = document.querySelectorAll('input[name="source-type"]');
  const panels = {
    manual: $('src-manual'),
    all_a:  $('src-all-a'),
    wencai: $('src-wencai'),
  };
  function update() {
    const val = document.querySelector('input[name="source-type"]:checked').value;
    for (const [k, el] of Object.entries(panels)) {
      if (el) el.classList.toggle('hidden', k !== val);
    }
  }
  radios.forEach(r => r.addEventListener('change', update));
  update();
}

// ── 全 A 只数警告联动 ─────────────────────────────────────────────────
function bindAllALimitWatch() {
  const inp = $('all-a-limit');
  if (!inp) return;
  function update() {
    const v = parseInt(inp.value, 10) || 0;
    const warnEl     = $('all-a-warn');
    const warnText   = $('all-a-warn-text');
    const confirmRow = $('all-a-confirm-row');
    const cb         = $('all-a-confirm');
    if (v >= 500) {
      if (warnEl)   warnEl.classList.remove('hidden');
      if (warnText) warnText.textContent = `扫描 ${v} 只股票，耗时可能超过 10 分钟。请勾选确认后才能运行。`;
      if (confirmRow) confirmRow.classList.remove('hidden');
    } else if (v >= 300) {
      if (warnEl)   warnEl.classList.remove('hidden');
      if (warnText) warnText.textContent = `扫描 ${v} 只股票，耗时可能较长（几分钟），请注意。`;
      if (confirmRow) confirmRow.classList.add('hidden');
      if (cb) cb.checked = false;
    } else {
      if (warnEl)   warnEl.classList.add('hidden');
      if (confirmRow) confirmRow.classList.add('hidden');
      if (cb) cb.checked = false;
    }
  }
  inp.addEventListener('input', update);
  update();
}

// ── 构建策略 JSON ─────────────────────────────────────────────────────
function buildStrategy() {
  const sourceType = document.querySelector('input[name="source-type"]:checked').value;

  let source = { type: sourceType };
  if (sourceType === 'manual') {
    const raw   = $('manual-codes').value.trim();
    const codes = raw.split(/[\s,，\n]+/).map(s => s.trim()).filter(Boolean);
    if (codes.length === 0) throw new Error('手动来源：请输入至少一个代码');
    source.codes = codes;
  } else if (sourceType === 'all_a') {
    source.limit = parseInt($('all-a-limit').value, 10) || 50;
  } else if (sourceType === 'wencai') {
    source.query = $('wencai-query').value.trim();
    if (!source.query) throw new Error('问财来源：请输入选股语句');
    source.limit = parseInt($('wencai-limit').value, 10) || 50;
  }

  const skills = [];
  document.querySelectorAll('#skill-list input[type=checkbox]:checked').forEach(cb => {
    // 双重防守：灰色技能 disabled 不会出现在 :checked 中，但万一 DOM 被篡改也过滤掉
    if (LIVE_SKILL_IDS.has(cb.value)) skills.push(cb.value);
  });
  if (skills.length === 0) throw new Error('请至少选择一项技能');

  const pathType = document.querySelector('input[name="path-type"]:checked').value;

  // 收集 skill-scoped 参数
  const skillParams = {};
  for (const skillId of skills) {
    const defs = SKILL_PARAMS[skillId] || [];
    if (defs.length === 0) continue;
    const sp = {};
    for (const pd of defs) {
      const el = $(`p-${skillId}-${pd.name}`);
      if (!el) continue;
      let val;
      if (pd.type === 'int')   val = parseInt(el.value, 10);
      else if (pd.type === 'float') val = parseFloat(el.value);
      else if (pd.type === 'bool') val = el.value === 'true';
      else val = el.value;
      if (!isNaN(val) || typeof val === 'string') sp[pd.name] = val;
    }
    if (Object.keys(sp).length > 0) skillParams[skillId] = sp;
  }

  return {
    source,
    skills,
    path_type: pathType,
    params: { skills: skillParams },
  };
}

// ── 恢复默认参数按钮 ──────────────────────────────────────────────────
function bindResetParams() {
  const btn = $('btn-reset-params');
  if (btn) btn.onclick = () => { resetParams(); };
}

// ── 运行按钮 ──────────────────────────────────────────────────────────
$('btn-run') && ($('btn-run').onclick = async () => {
  let strategy;
  try {
    strategy = buildStrategy();
  } catch (e) {
    showAlert('center-alerts', 'danger', e.message);
    return;
  }
  saveParams();   // 保存本次参数（总纲第十一章回显）

  // 全 A 扫描保护（双层：前端 + API）
  if (strategy.source.type === 'all_a') {
    const limit = strategy.source.limit || 0;
    if (limit >= 500) {
      const cb = $('all-a-confirm');
      if (!cb || !cb.checked) {
        showAlert('center-alerts', 'warn', `全 A 扫描 ${limit} 只需要勾选"确认继续"才能运行。`);
        return;
      }
      strategy.confirm_large_scope = true;
    } else if (limit >= 300) {
      strategy.confirm_large_scope = true;
    }
  }

  clearResult();
  stopPoll();
  logClear();
  _lastEventCount = 0;

  $('btn-run').disabled = true;
  $('run-spinner').classList.remove('hidden');
  setStatus('pending');
  logLine('HEAD', `启动策略: 来源=${strategy.source.type}  技能=[${strategy.skills.join(',')}]  路径=${strategy.path_type}`);

  try {
    const res = await fetch(API.run, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(strategy),
    });
    if (res.status === 409) {
      const errData = await res.json().catch(() => ({}));
      const msg = errData.error || '已有任务正在运行，请稍候…';
      showAlert('center-alerts', 'warn', msg);
      $('btn-run').disabled = false;
      $('run-spinner').classList.add('hidden');
      setStatus('idle');
      return;
    }
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      showAlert('center-alerts', 'danger', errData.error || `启动失败（HTTP ${res.status}）`);
      $('btn-run').disabled = false;
      $('run-spinner').classList.add('hidden');
      setStatus('error');
      return;
    }
    const data = await res.json();
    $('run-id').textContent = data.run_id || '';
    logLine('INFO', `run_id=${data.run_id}  状态=${data.status}`);
    startPoll();
  } catch (e) {
    showAlert('center-alerts', 'danger', `启动失败: ${e.message}`);
    $('btn-run').disabled = false;
    $('run-spinner').classList.add('hidden');
    setStatus('error');
  }
});

// ── 轮询 /api/stream?since=N ──────────────────────────────────────────
function startPoll() {
  _pollTimer = setInterval(pollStream, 1500);
}
function stopPoll() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

async function pollStream() {
  try {
    const res  = await fetch(`${API.stream}?since=${_lastEventCount}`);
    const data = await res.json();

    setStatus(data.status || 'idle');
    if (data.run_id) $('run-id').textContent = data.run_id;

    // 追加新事件（服务器返回 since 之后的所有新事件）
    const newEvents = data.events || [];
    newEvents.forEach(ev => logLine(ev.level, ev.msg));
    // 用服务器的 event_count 更新游标，避免任何截断
    if (data.event_count != null) _lastEventCount = data.event_count;

    if (data.status === 'completed' || data.status === 'error') {
      stopPoll();
      $('btn-run').disabled = false;
      $('run-spinner').classList.add('hidden');
      await fetchResult();
    }
  } catch (e) {
    logLine('WARN', `轮询异常: ${e.message}`);
  }
}

// ── 拉取结果 ──────────────────────────────────────────────────────────
async function fetchResult() {
  try {
    const res = await fetch(API.result);
    if (!res.ok) {
      showAlert('center-alerts', 'warn', `拉取结果失败: HTTP ${res.status}`);
      return;
    }
    _lastResult = await res.json();
    renderResult(_lastResult);
  } catch (e) {
    showAlert('center-alerts', 'danger', `拉取结果异常: ${e.message}`);
  }
}

// ── 渲染结果 ──────────────────────────────────────────────────────────
function renderResult(r) {
  renderCoverage(r);
  renderPrefetch(r);
  renderReadiness(r);
  renderWarnings(r);
  renderProducers(r);
  renderHits(r);
  renderFailed(r);
  renderReportLinks(r);
}

function renderPrefetch(r) {
  const el = $('prefetch-box');
  if (!el) return;
  const triggered = r.prefetch_triggered;
  const pr = triggered ? (r.prefetch_report || {}) : null;

  if (!triggered || !pr || Object.keys(pr).length === 0) {
    el.innerHTML = '<div class="alert alert-info"><span class="alert-icon">ℹ️</span>'
      + '<span>本轮未触发预热，使用已有缓存（未访问 baostock / akshare / yfinance）</span></div>';
    return;
  }

  // 计算数据延迟（stale_days）
  const dtm = pr.data_time_max ? String(pr.data_time_max).slice(0, 10) : null;
  let staleDays = '—';
  let staleNote = '';
  if (dtm) {
    try {
      const diff = Math.round((Date.now() - new Date(dtm + 'T00:00:00').getTime()) / 86400000);
      staleDays = diff;
      if (diff >= 2)
        staleNote = `⚠ 数据明显过旧（最新 ${dtm}，距今 ${diff} 自然日），请谨慎使用`;
      else if (diff >= 1)
        staleNote = `⚠ 数据可能滞后（最新 ${dtm}，距今 ${diff} 自然日）`;
    } catch (_) {}
  }

  const rows = [
    ['命中缓存',    pr.cache_hit      ?? '—', 'text-green'],
    ['新拉成功',    pr.fetched_ok     ?? '—', 'text-green'],
    ['补拉恢复',    pr.recovered_count ?? 0,  'text-green'],
    ['最终失败',    pr.failed         ?? '—', 'text-red'],
    ['Stale 降级',  pr.stale_used     ?? '—', 'text-yellow'],
    ['K线最新日期', dtm || '—',               ''],
    ['数据延迟',    staleDays === '—' ? '—' : `${staleDays} 自然日`, ''],
  ];
  const rowsHtml = rows.map(([label, val, cls]) =>
    `<div class="cov-item"><span class="cov-label">${esc(label)}</span>`
    + `<span class="cov-value ${cls}">${esc(String(val))}</span></div>`
  ).join('');

  el.innerHTML = `<div class="coverage-grid">${rowsHtml}</div>`
    + (staleNote
      ? `<div class="alert alert-warn" style="margin-top:6px">`
        + `<span class="alert-icon">⚠️</span><span>${esc(staleNote)}</span></div>`
      : '');
}

function renderReadiness(r) {
  const dc       = r.data_coverage || {};
  const readiness = dc.readiness || 'unknown';
  const el = $('readiness-box');
  el.innerHTML = '';

  const types = {
    aborted: { cls: 'alert-danger', icon: '⛔', text: `readiness=aborted  失败率 ${pct(dc.failure_rate)}  数据严重不足，结果不可信` },
    partial:  { cls: 'alert-warn',  icon: '⚠️', text: `readiness=partial  部分数据缺失，结果仅供参考` },
    ready:    { cls: 'alert-ok',    icon: '✅', text: `readiness=ready  数据充足` },
  };
  const t = types[readiness] || { cls: 'alert-info', icon: 'ℹ️', text: `readiness=${readiness}` };
  const div = document.createElement('div');
  div.className = `alert ${t.cls}`;
  div.innerHTML = `<span class="alert-icon">${t.icon}</span><span>${t.text}</span>`;
  el.appendChild(div);
}

function renderCoverage(r) {
  const dc  = r.data_coverage || {};
  $('coverage-box').innerHTML = `
    <div class="coverage-grid">
      <div class="cov-item"><span class="cov-label">scope 总数</span><span class="cov-value">${dc.scope_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">有缓存</span><span class="cov-value text-green">${dc.cached_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">缺失缓存</span><span class="cov-value text-yellow">${dc.missing_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">失败</span><span class="cov-value text-red">${dc.failed_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">Stale</span><span class="cov-value text-yellow">${dc.stale_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">失败率</span><span class="cov-value">${pct(dc.failure_rate)}</span></div>
    </div>`;
}

function renderWarnings(r) {
  const warnings  = r.warnings || [];
  const exprMeta  = (r.expression || {}).metadata || {};
  const softFilters = exprMeta.soft_filter_skills || [];
  const weakSignals = exprMeta.weak_signal_skills || [];

  const extra = [];
  if (softFilters.length) extra.push(`⚠ SMC soft_filter 模式（${softFilters.join(',')}）：结果为软过滤/透传，非 strict 正向命中`);
  if (weakSignals.length) extra.push(`⚠ 波浪弱信号（${weakSignals.join(',')}）：no_top 放行，不应视为强正向信号`);

  const all = [...extra, ...warnings];
  const el  = $('warnings-box');
  if (!all.length) {
    el.innerHTML = '<span class="text-muted" style="font-size:11px">无警告</span>';
    return;
  }
  el.innerHTML = all.map(w =>
    `<div class="warning-item"><span>⚠</span><span>${esc(w)}</span></div>`
  ).join('');
}

function renderProducers(r) {
  const el    = $('producer-box');
  const prods = r.producer_summary || [];
  if (!prods.length) { el.innerHTML = '<span class="text-muted">—</span>'; return; }

  el.innerHTML = prods.map(p => {
    const modeTag = p.mode === 'soft_filter'
      ? '<span class="tag tag-debug">soft_filter</span>'
      : p.mode === 'strict' ? '<span class="tag tag-strict">strict</span>'
      : '';
    const semTag = p.hit_semantics === 'negative'
      ? '<span class="tag tag-neg">负向</span>' : '';
    const name = p.skill_name || p.skill_id || '?';
    return `
      <div class="prod-row">
        <span class="prod-name">${esc(name)} ${semTag} ${modeTag}</span>
        <span class="prod-stats">命中 ${p.hit_count ?? '-'} / 未中 ${p.miss_count ?? '-'}${p.duration_seconds != null ? `  ${p.duration_seconds}s` : ''}</span>
      </div>`;
  }).join('');
}

function renderHits(r) {
  const hits     = r.explanations || [];
  const codes    = r.final_hit_codes || [];
  const exprMeta = (r.expression || {}).metadata || {};
  const softFilters = new Set(exprMeta.soft_filter_skills || []);
  const weakSignals = new Set(exprMeta.weak_signal_skills || []);

  $('hit-count').textContent = codes.length;

  const el = $('hit-list');
  if (!hits.length) {
    el.innerHTML = '<span class="text-muted" style="font-size:12px">暂无命中</span>';
    return;
  }

  el.innerHTML = hits.map((h, idx) => {
    const evId = `hit-ev-${idx}`;
    const tags = [];
    if (h.uses_hfq)             tags.push('<span class="tag tag-ok">后复权</span>');
    if (h.has_soft_filter_mode) tags.push('<span class="tag tag-debug">soft_filter</span>');
    if (h.has_weak_signal)      tags.push('<span class="tag tag-weak">弱信号</span>');
    (h.skill_hits || []).forEach(s => {
      if (softFilters.has(s.skill_id))      tags.push(`<span class="tag tag-debug">${esc(s.skill_name)}</span>`);
      else if (weakSignals.has(s.skill_id)) tags.push(`<span class="tag tag-weak">${esc(s.skill_name)}</span>`);
      else tags.push(`<span class="tag" style="background:#1e3a5f;color:#93c5fd">${esc(s.skill_name)}</span>`);
    });

    // 证据明细（展开后显示）
    const skillHits = h.skill_hits || [];
    const evidenceRows = skillHits.length
      ? skillHits.map(s => `
          <div class="evidence-item">
            <span class="evidence-skill">${esc(s.skill_name)}</span>
            <span class="evidence-reason">${esc(s.reason_cn || '命中（无详细说明）')}</span>
          </div>`).join('')
      : '<span class="text-muted" style="font-size:11px">无详细证据</span>';

    const dataIssues = (h.data_quality_issues || []).map(q =>
      `<div class="evidence-item"><span class="evidence-skill" style="color:var(--yellow)">数据</span><span class="evidence-reason">${esc(q)}</span></div>`
    ).join('');

    return `
      <div class="hit-card">
        <div class="hit-header" onclick="toggleEvidence('${evId}', this)">
          <span class="hit-code">${esc(h.code)}</span>
          <span class="hit-toggle">▶</span>
        </div>
        <div class="hit-expl">${esc(h.explanation_cn || '')}</div>
        ${tags.length ? `<div class="hit-tags">${tags.join('')}</div>` : ''}
        <div class="hit-evidence" id="${evId}">
          ${evidenceRows}${dataIssues}
        </div>
      </div>`;
  }).join('');
}

window.toggleEvidence = function(evId, headerEl) {
  const ev = document.getElementById(evId);
  if (!ev) return;
  const isOpen = ev.classList.toggle('open');
  const toggle = headerEl && headerEl.querySelector('.hit-toggle');
  if (toggle) toggle.textContent = isOpen ? '▼' : '▶';
};

function renderFailed(r) {
  const failed = r.failed_codes || [];
  const stale  = r.stale_codes  || [];

  const felEl = $('failed-list');
  if (!failed.length) {
    felEl.innerHTML = '<span class="text-muted">无失败代码</span>';
  } else {
    felEl.innerHTML = failed.map(c => `<div class="failed-code">${esc(c)}</div>`).join('');
  }

  const stEl = $('stale-list');
  if (!stale.length) {
    stEl.classList.add('hidden');
  } else {
    stEl.classList.remove('hidden');
    stEl.innerHTML = '<b>Stale：</b>' + stale.map(c => esc(c)).join(', ');
  }
}

function renderReportLinks(r) {
  const el    = $('report-links');
  const runId = r.run_id || '';
  el.innerHTML = `
    <a class="report-link" href="/api/result" target="_blank">
      📄 执行结果 JSON（run_id: ${esc(runId)}）
    </a>
    <a class="report-link" href="#" onclick="downloadReport(event)">
      📋 查看报告路径
    </a>`;
}

window.downloadReport = function(e) {
  e.preventDefault();
  if (!_lastResult) return;
  alert(`报告路径：output/current/run_report.md\n归档路径：output/runs/${_lastResult.run_id}/run_report.md\n也可直接 GET /api/result 查看完整 JSON。`);
};

// ── 辅助函数 ──────────────────────────────────────────────────────────
function setStatus(status) {
  const el  = $('status-badge');
  const map = {
    idle:      ['badge-idle',      '待机'],
    pending:   ['badge-pending',   '排队中'],
    running:   ['badge-running',   '运行中'],
    completed: ['badge-completed', '完成'],
    error:     ['badge-error',     '错误'],
    aborted:   ['badge-aborted',   '已中止'],
  };
  const [cls, text] = map[status] || ['badge-idle', status];
  el.className  = `badge ${cls}`;
  el.textContent = text;
}

function logLine(level, msg) {
  const box = $('log-box');
  const div = document.createElement('div');
  div.className = 'log-line';
  const ts = new Date().toTimeString().slice(0, 8);
  div.innerHTML = `<span class="log-ts">${ts}</span><span class="log-${level}">${esc(msg)}</span>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function logClear() {
  $('log-box').innerHTML = '';
}

function clearResult() {
  $('hit-count').textContent = '—';
  $('hit-list').innerHTML    = '';
  $('failed-list').innerHTML = '';
  $('stale-list').classList.add('hidden');
  $('coverage-box').innerHTML  = '';
  $('prefetch-box').innerHTML  = '';
  $('readiness-box').innerHTML = '';
  $('warnings-box').innerHTML  = '';
  $('producer-box').innerHTML  = '';
  $('report-links').innerHTML  = '';
  _lastResult = null;
}

function showAlert(containerId, type, msg) {
  const el = $(containerId);
  if (!el) return;
  const div = document.createElement('div');
  const icons = { danger: '❌', warn: '⚠️', info: 'ℹ️', ok: '✅' };
  div.className = `alert alert-${type}`;
  div.innerHTML = `<span class="alert-icon">${icons[type] || 'ℹ️'}</span><span>${esc(msg)}</span>`;
  el.appendChild(div);
  setTimeout(() => div.remove(), 8000);
}

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function pct(v) {
  if (v == null) return '—';
  return (v * 100).toFixed(1) + '%';
}
