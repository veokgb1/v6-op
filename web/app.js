/* V6OP 操盘台 — app.js (V6OP-029) */
'use strict';

// ── API 路由 ──────────────────────────────────────────────────────────
const API = {
  health:       '/api/health',
  run:          '/api/run',
  result:       '/api/result',
  stream:       '/api/stream',
  abort:        '/api/abort',
  scanSectors:  '/api/scan_sectors',
  runs:         '/api/runs',
  wencaiStatus: '/api/wencai/status',
};

// ── P1-P6 预设策略（来自 V5 PRESET_QUERIES）─────────────────────────
const PRESET_QUERIES = {
  P1: "属于半导体或人工智能概念，非ST，上市时间大于1年，流通市值在80亿到300亿之间，今日量比大于1.5，近5日主力资金呈净流入，且今日收盘价站上20日均线",
  P2: "非ST，非停牌，近60日区间跌幅大于30%，今日涨幅大于3%，今日成交额大于3亿，且今日换手率大于近5日平均换手率的1.5倍",
  P3: "非ST，近30日振幅小于15%，今日盘中最大涨幅大于7%，但今日收盘涨幅小于4%，流通市值小于150亿",
  P4: "剔除ST股，剔除上市天数小于300天，近60日跌幅大于20%，近5日内出现过涨停，今日收盘价大于20日均线，且今日换手率大于5%小于15%的股票",
  P5: "流通市值在30亿到150亿之间，近30日振幅小于15%的A股",
  P6: "属于人工智能或低空经济概念，市净率PB小于4，机构持股比例大于10%，且近3日主力资金净流入排名前30的A股",
};

// ── 收藏 localStorage Key ─────────────────────────────────────────────
const FAV_KEY_WENCAI = 'v6op_wencai_favorites';
const FAV_KEY_SECTOR = 'v6op_sector_favorites';

// ── 页面小 i 帮助 ───────────────────────────────────────────────────
const HELP_TEXT = {
  'data-markers': {
    title: '数据标记是什么',
    body: [
      '这里不是让你记路径，而是告诉你这一轮用到了哪几类数据。',
      '★ 来源快照：本轮问财、全A或手输得到的股票池。它像本轮名单，下一次启动可能会覆盖。',
      '★★ K线数据库：已经保存到本机的行情K线数据。只要你不清理它，电脑重启后还在。',
      '★★★ 技能结果库：某批股票、某组参数、某个K线日期算出来的技能结果。条件一样时可以复用，条件变了就会重新算。'
    ],
  },
  'source-snapshot': {
    title: '★ 来源快照',
    body: [
      '它是本轮股票池，也就是这次从问财、全A或手输里拿到的股票名单。',
      '它会写到当前结果里，方便看本轮从多少只开始。',
      '它不是长期数据库，下一次启动管道可能会重新生成并覆盖。'
    ],
  },
  'kline-db': {
    title: '★★ K线数据库',
    body: [
      '这是本机保存的股票K线数据，SMC、K线形态、缠论、波浪、排雷都主要读它。',
      '它是磁盘文件，不是内存。只要你不清理这个数据库，电脑重启后还在。',
      '如果这里显示已够用，意思是这批股票需要的K线本机已经有了，本轮不用再去行情源重新拿。'
    ],
  },
  'skill-result-store': {
    title: '★★★ 技能结果库',
    body: [
      '这是技能算完以后留下的结果，比如同一批股票用同一组SMC参数算过一次。',
      '只要股票池、参数、K线日期都一样，下次可以直接复用，少算一遍。',
      '如果你改了参数、换了股票池，或者K线日期更新了，它会重新计算。'
    ],
  },
  'fetch-record': {
    title: '本轮取数记录',
    body: [
      '“本轮”就是你按一次启动管道。',
      '这里的“取数”主要指给当前股票池准备K线行情数据，不是问财语句，也不是技能结果。',
      '如果本机没有某只股票的K线，它会去行情源拿；如果本机已经有，就直接用本机保存的数据。',
      '所以“本轮不用重新取数”可以理解成：这批股票要用的K线本机已有，直接开算。'
    ],
  },
  'param-czsc-signal': {
    title: '缠论：买点窗口',
    body: [
      '意思是：只看最近 N 根K线里有没有一买、二买、三买。默认 5，就是最近5根K线内出现买点才算命中。',
      'N 小一点更严格，更偏“刚刚出现的买点”，信号更新鲜，但容易漏掉前几天刚出现的机会。',
      'N 大一点更宽松，比如 10 或 15，会把更早出现的买点也算进来，命中会变多，但信号可能没那么新。',
      '举例：今天是第0根，如果3天前出现二买，窗口=5 会保留；如果8天前出现二买，窗口=5 不保留，窗口=10 才可能保留。'
    ],
  },
  'param-czsc-buy-type': {
    title: '缠论：买点类型',
    body: [
      '这里选择一买、二买、三买或全部。它不是“一码二码”，而是缠论里的第一类、第二类、第三类买点。',
      '全部最宽松，只要识别到任一种买点就通过。',
      '只选二买会更聚焦，但股票会少；适合你明确只想看某一种买点结构的时候。'
    ],
  },
  'param-kline-signal': {
    title: 'K线：形态窗口',
    body: [
      '意思是：最近 N 根K线内有没有系统认为偏正向的K线形态，比如锤子线、吞没、启明星、三白兵等。',
      '这里的“有形态”主要指能作为正向参考的形态，不是所有坏形态都算通过。坏形态不会帮它命中。',
      '默认 5 比较偏近期。调小到 3 会更严格、更看新鲜信号；调大到 10 会更宽松，命中更多，但可能把较早的形态也算进去。',
      '如果你在做短线筛选，5 通常够用；如果想别漏掉刚启动几天的形态，可以试 8 到 10。'
    ],
  },
  'param-kline-body': {
    title: 'K线：实体阈值',
    body: [
      '实体阈值用于判断K线身体是不是足够明显。这里的实体大致是开盘价和收盘价之间的距离。',
      '默认 0.1 表示实体相对整根K线振幅不能太小。调大更严格，只保留身体更明显的K线；调小更宽松，小实体也可能参与判断。',
      '数值太小会让十字星、小实体线更多进入判断，信号会杂；数值太大会漏掉一些温和启动的K线。'
    ],
  },
  'param-kline-shadow': {
    title: 'K线：影线倍数',
    body: [
      '影线倍数用于识别长上影、长下影这类形态。影线越长，说明盘中冲高回落或探底回升越明显。',
      '默认 2.0，意思是影线长度大约要达到实体的2倍，才算比较明显。',
      '调大到 2.5 或 3 会更严格，只认很长的影线；调小到 1.5 会更宽松，但噪音也会更多。',
      '例如看锤子线时，长下影越明显越像探底回升；但如果门槛太低，普通小波动也可能被看成形态。'
    ],
  },
  'param-kline-neutral': {
    title: 'K线：中性放行',
    body: [
      '“否”是默认正式用法：必须有正向形态才通过。',
      '“是”表示中性形态也允许通过，股票会变多，但筛选会变松。',
      '如果你是在正式选股，建议先保持“否”。如果你只是想扩大候选池，再交给 SMC、缠论或评分层判断，可以临时改成“是”。'
    ],
  },
  'param-smc-signal': {
    title: 'SMC：信号窗口',
    body: [
      '意思是：最近 N 根K线内有没有 BOS、ChoCH、FVG 这类聪明钱结构信号。',
      '默认 15 比 K线形态的 5 更宽，是因为 SMC 结构信号不一定每天出现，需要给它稍长一点观察范围。',
      '调小更严格，要求信号非常近；调大更宽松，会把更早出现的结构也算进来。',
      '如果你发现 SMC 总是命中太少，可以试 20；如果你只要非常近的结构，可以降到 8 到 10。'
    ],
  },
  'param-smc-swing': {
    title: 'SMC：摆动窗口',
    body: [
      '摆动窗口用于识别结构高点和低点。简单说，它决定系统用多宽的视野去找“前高、前低”。',
      '数值小，会更敏感，小波动也容易被当成结构；命中可能更多，但噪音也更多。',
      '数值大，会更稳，只认更明显的结构高低点；信号更少，但通常更干净。',
      '默认 10 是折中。短线想灵敏可以小一点；想减少假突破，可以大一点。'
    ],
  },
  'param-smc-close-break': {
    title: 'SMC：收盘突破',
    body: [
      '选择“是”：要求收盘价确认突破结构位，比较严格，假突破少一些。',
      '选择“否”：盘中或结构上出现突破迹象也可能放行，比较宽松，命中会多一些。',
      '正式筛选建议先用“是”。如果市场很快、你想提前看候选，可以临时用“否”。'
    ],
  },
  'param-smc-mode': {
    title: 'SMC：分析模式',
    body: [
      'strict 是正式路径：SMC 必须真的命中，才算通过。正式跑结果建议用这个。',
      'soft_filter 是调试/透传：不会因为 SMC 不命中就直接杀掉股票，但会标注它是软过滤。适合你想看“如果不让 SMC 卡死，会剩什么”。',
      'bypass 是完全透传：SMC 等于不参与筛选，所有输入都通过。适合排查问题，不适合作为正式选股结论。',
      '一句话：正式用 strict；调试用 soft_filter；怀疑 SMC 有问题时才用 bypass。'
    ],
  },
  'param-wave-signal': {
    title: '波浪：波浪回看',
    body: [
      '意思是：最近 N 根K线内检查有没有波浪相关信号。',
      '默认 20，比 K线形态更长，因为波浪结构需要一段走势才能形成。',
      '调小更严格，只看很近的波浪；调大更宽松，会看更长一段走势，但也可能把老结构带进来。',
      '波浪在这里主要是辅助过滤：ABC底部放行，明显5浪顶部会拦截。'
    ],
  },
  'param-wave-swing': {
    title: '波浪：Swing窗口',
    body: [
      'Swing窗口用于找波峰、波谷，也就是波浪的拐点。你可以理解成“拐点识别半径”。',
      '数值小，系统更敏感，容易找出很多小波峰小波谷，适合短线，但噪音多。',
      '数值大，系统只认更明显的大拐点，结构更稳，但可能漏掉短线波浪。',
      '默认 10 是折中。如果图形太碎，可以调大；如果总是识别不到，可以调小。'
    ],
  },
  'param-wave-fib': {
    title: '波浪：Fib容差',
    body: [
      'Fib 是 Fibonacci 比例，波浪里常看回撤比例，比如 0.382、0.5、0.618。',
      '容差就是允许偏离标准比例多少。默认 0.15，表示不用完全卡死在标准比例上。',
      '调小更严格，只有更接近标准比例的结构才算；调大更宽松，命中更多，但可能把不像样的结构也算进去。',
      '正式初期建议先保持默认，不要太小，否则很容易一个都识别不到。'
    ],
  },
  'param-wave-min-bars': {
    title: '波浪：每浪最少K线',
    body: [
      '意思是：每一段浪至少要包含多少根K线，才承认它是一段有效波浪。',
      '默认 5，表示每段浪至少要有5根K线，避免把一两根K线的小抖动当成一浪。',
      '调大更严格，只认更完整的波段；调小更敏感，但容易把噪音当波浪。',
      '如果你想贴近 V5，先保持 5。'
    ],
  },
  'stress-guide': {
    title: '压力测试怎么理解',
    body: [
      '全 A 股现在走本地A股名单全量，不再按 300 / 500 / 2000 / 5000 档位截断。',
      '问财现在默认不限档位，会自动翻页直到没有新增股票；实际能返回多少以问财接口为准。',
      '如果把缠论、K线、SMC、波浪、排雷全部勾上并且走并行取交集，结果为 0 很正常。这表示所有正向条件同时命中的股票没有，不一定是系统坏。',
      '重新点“启动管道”不会自动清掉 K线数据库。已经保存到本机的K线通常还会复用，电脑重启后也还在。',
      '问财来源本轮会重新查一次；后面是否能复用，主要看 K线数据库和技能结果库。以后可以再做“使用上一轮来源池继续跑”的按钮。',
      '技能结果库的复用条件比较严格：同一批股票、同一组参数、同一个K线日期才复用。你换路径后，如果某个技能的输入股票池变了，就可能重新算这个技能，但一般仍然不需要重新下载K线。',
      '顺序漏斗：第一个技能吃全池，第二个技能只吃第一个剩下的股票。并行取交集：每个技能都吃同一个全池，然后取交集。简单混合：前两个正向技能先并行取交集，后面的再顺序过滤。',
      '推荐测试法：先少勾一点，例如“缠论 + 排雷”或“K线 + 排雷”跑通；再加 SMC、波浪；最后再试全技能硬交集。'
    ],
  },
};

// ── 技能元数据 ────────────────────────────────────────────────────────
const SKILL_META = {
  czsc:     { label: '缠论买点',  note: '一买/二买/三买买点检测，只读本地K线数据', semantics: 'positive' },
  smc:      { label: 'SMC 聪明钱', note: 'BOS/ChoCH/FVG 聪明钱信号，只读本地K线数据', semantics: 'positive' },
  kline:    { label: 'K线形态',   note: '15种形态分析（锤子/吞没/启明星等），纯本地', semantics: 'positive' },
  wave:     { label: '波浪分析',  note: 'ABC底放行、5浪顶拦截；无顶部信号也放行', semantics: 'positive' },
  landmine: { label: '排雷过滤',  note: '负向过滤：北交所/ST/K线不足/本地K线缺失', semantics: 'negative' },
};

// 灰色技能列表由 /api/skill_catalog 动态装载
let SKILL_CATALOG_GRAY = [];

// 每个技能的可调参数
const SKILL_PARAMS = {
  czsc: [
    { name: 'signal_bars', label: '买点窗口', hint: '近 N 根 K 线内有买点才保留', type: 'int',   default: 5, help: 'param-czsc-signal' },
    { name: 'buy_type',    label: '买点类型', hint: '一买/二买/三买 或全部',       type: 'select',
      options: [{v:'all',l:'全部'},{v:'1st',l:'一买'},{v:'2nd',l:'二买'},{v:'3rd',l:'三买'}],
      default: 'all', help: 'param-czsc-buy-type' },
    { name: 'days',        label: '回看天数', hint: '加载最近 N 天 K 线',           type: 'int',   default: 365 },
  ],
  smc: [
    { name: 'signal_bars',  label: '信号窗口', hint: '近 N 根内有 BOS/ChoCH/FVG 才保留', type: 'int', default: 15, help: 'param-smc-signal' },
    { name: 'swing_length', label: '摆动窗口', hint: '识别结构高低点的观察范围', type: 'int', default: 10, help: 'param-smc-swing' },
    { name: 'close_break',  label: '收盘突破', hint: '是：要求收盘价确认突破；否：放宽确认', type: 'bool', default: true, help: 'param-smc-close-break' },
    { name: 'mode',         label: '分析模式', hint: 'strict=正式路径  soft_filter=调试透传',
      type: 'select',
      options: [
        {v:'strict',     l:'strict（正式路径）'},
        {v:'soft_filter',l:'soft_filter（调试/透传）— 标注为软过滤'},
        {v:'bypass',     l:'bypass（透传所有）'},
      ],
      default: 'strict', help: 'param-smc-mode' },
    { name: 'days', label: '回看天数', hint: '加载最近 N 天 K 线', type: 'int', default: 365 },
  ],
  kline: [
    { name: 'signal_bars',  label: '形态窗口', hint: '近 N 根内有形态才保留',     type: 'int',   default: 5, help: 'param-kline-signal' },
    { name: 'body_pct',     label: '实体阈值', hint: '十字星：实体/振幅比例下限', type: 'float', default: 0.1, help: 'param-kline-body' },
    { name: 'shadow_ratio', label: '影线倍数', hint: '影线 ÷ 实体长度阈值',        type: 'float', default: 2.0, help: 'param-kline-shadow' },
    { name: 'pass_neutral', label: '中性放行', hint: '是：中性形态也可通过；否：必须有正向形态', type: 'bool', default: false, help: 'param-kline-neutral' },
    { name: 'days',         label: '回看天数', hint: '加载最近 N 天 K 线',         type: 'int',   default: 365 },
  ],
  wave: [
    { name: 'signal_bars',   label: '波浪回看',   hint: '近 N 根内检查波浪信号', type: 'int', default: 20, help: 'param-wave-signal' },
    { name: 'swing_window',  label: 'Swing窗口',  hint: '识别波峰波谷的观察半径', type: 'int', default: 10, help: 'param-wave-swing' },
    { name: 'fib_tolerance', label: 'Fib容差',    hint: 'Fibonacci 比例允许偏差', type: 'float', default: 0.15, help: 'param-wave-fib' },
    { name: 'min_wave_bars', label: '每浪最少K线', hint: '每段浪至少 N 根 K 线，V5 默认 5', type: 'int', default: 5, help: 'param-wave-min-bars' },
    { name: 'days',          label: 'K线回看',    hint: '加载最近 N 天 K 线',    type: 'int', default: 365 },
  ],
  landmine: [],
};

// ── 状态 ──────────────────────────────────────────────────────────────
let _pollTimer       = null;
let _lastResult      = null;
let _lastEventCount  = 0;
let _resultFetchedForRunId = null;
let _currentRunStatus = 'idle';
let _wencaiMode      = 'stock';  // 'stock' | 'sector'
let _confirmedSectors = [];      // Phase A 已确认板块

function getWencaiMode() {
  return _wencaiMode;
}

function getConfirmedSectors() {
  return [..._confirmedSectors];
}

function notifyStrategyStateChanged() {
  document.dispatchEvent(new CustomEvent('v6op:strategy-state-change'));
}

function getRunScopeLimit() {
  const el = $('run-scope-limit');
  if (!el) return 0;
  const n = parseInt(el.value || '0', 10);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

function runScopeText(limit = getRunScopeLimit()) {
  return limit > 0 ? `测试 ${limit}` : '全量';
}

// ── DOM 引用 ──────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const LIVE_SKILL_IDS = new Set(Object.keys(SKILL_META));

// ── 参数持久化 ────────────────────────────────────────────────────────
const PARAMS_STORE_ID = 'v6op_last_params';

function getSkillOrder() {
  return Array.from(document.querySelectorAll('#skill-list .skill-item[data-skill-id]'))
    .map(item => item.dataset.skillId)
    .filter(Boolean);
}

function applySkillOrder(order) {
  const container = $('skill-list');
  if (!container || !Array.isArray(order) || order.length === 0) return;
  const graySection = container.querySelector('.v6-gray-section');
  const items = new Map(
    Array.from(container.querySelectorAll('.skill-item[data-skill-id]'))
      .map(item => [item.dataset.skillId, item])
  );
  const desired = [...order, ...Object.keys(SKILL_META)].filter((id, idx, arr) =>
    items.has(id) && arr.indexOf(id) === idx
  );
  desired.forEach(id => container.insertBefore(items.get(id), graySection || null));
  updateSkillMoveButtons();
}

function updateSkillMoveButtons() {
  const items = Array.from(document.querySelectorAll('#skill-list .skill-item[data-skill-id]'));
  items.forEach((item, idx) => {
    const up   = item.querySelector('[data-move="up"]');
    const down = item.querySelector('[data-move="down"]');
    if (up)   up.disabled   = idx === 0;
    if (down) down.disabled = idx === items.length - 1;
  });
}

function moveSkillItem(skillId, delta) {
  const items = Array.from(document.querySelectorAll('#skill-list .skill-item[data-skill-id]'));
  const idx = items.findIndex(item => item.dataset.skillId === skillId);
  const targetIdx = idx + delta;
  if (idx < 0 || targetIdx < 0 || targetIdx >= items.length) return;
  const item   = items[idx];
  const target = items[targetIdx];
  const parent = item.parentElement;
  if (!parent) return;
  if (delta < 0) parent.insertBefore(item, target);
  else           parent.insertBefore(target, item);
  updateSkillMoveButtons();
  saveParams();
  parent.dispatchEvent(new Event('change', { bubbles: true }));
}

function saveParams() {
  try {
    const sourceType = document.querySelector('input[name="source-type"]:checked')?.value || 'manual';
    const pathType   = document.querySelector('input[name="path-type"]:checked')?.value   || 'parallel_and';
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
    const wencaiQuery  = document.getElementById('wencai-query')?.value  || '';
    const wencaiLimit  = '0';
    const manualCodes  = document.getElementById('manual-codes')?.value  || '';
    const sectorQuery  = document.getElementById('sector-query')?.value  || '';
    const bridgeEnabled = !!document.getElementById('bridge-enabled')?.checked;
    const bridgeMode    = document.getElementById('bridge-mode')?.value || 'constrained';
    const bridgeQuery   = document.getElementById('bridge-query')?.value || '';
    const bridgeLimit   = '0';
    const runScopeLimit = getRunScopeLimit();
    const skillOrder   = getSkillOrder();

    const saved = {
      sourceType, pathType, skills, skillParams, skillOrder,
      wencaiQuery, wencaiLimit, manualCodes, wencaiMode: _wencaiMode, sectorQuery,
      bridgeEnabled, bridgeMode, bridgeQuery, bridgeLimit, runScopeLimit,
    };
    localStorage.setItem(PARAMS_STORE_ID, JSON.stringify(saved));
  } catch (_) {}
}

function restoreParams() {
  try {
    const raw = localStorage.getItem(PARAMS_STORE_ID);
    if (!raw) return;
    const saved = JSON.parse(raw);

    const srcRadio = document.querySelector(`input[name="source-type"][value="${saved.sourceType}"]`);
    if (srcRadio) { srcRadio.checked = true; srcRadio.dispatchEvent(new Event('change')); }

    const pathRadio = document.querySelector(`input[name="path-type"][value="${saved.pathType}"]`);
    if (pathRadio) pathRadio.checked = true;

    const runScope = document.getElementById('run-scope-limit');
    if (runScope && saved.runScopeLimit != null) runScope.value = String(saved.runScopeLimit);

    applySkillOrder(saved.skillOrder);

    const skillSet = new Set(saved.skills || []);
    document.querySelectorAll('#skill-list input[type=checkbox][data-live="true"]').forEach(cb => {
      const checked = skillSet.has(cb.value);
      if (cb.checked !== checked) {
        cb.checked = checked;
        cb.dispatchEvent(new Event('change'));
      }
    });

    if (saved.skillParams) {
      for (const [id, sp] of Object.entries(saved.skillParams)) {
        for (const [name, val] of Object.entries(sp)) {
          const el = document.getElementById(`p-${id}-${name}`);
          if (el) el.value = val;
        }
      }
    }

    const wq = document.getElementById('wencai-query');
    if (wq && saved.wencaiQuery) wq.value = saved.wencaiQuery;
    const wl = document.getElementById('wencai-limit');
    if (wl) wl.value = '0';
    const mc = document.getElementById('manual-codes');
    if (mc && saved.manualCodes) mc.value = saved.manualCodes;
    const sq = document.getElementById('sector-query');
    if (sq && saved.sectorQuery) sq.value = saved.sectorQuery;
    const be = document.getElementById('bridge-enabled');
    if (be) be.checked = !!saved.bridgeEnabled;
    const bm = document.getElementById('bridge-mode');
    if (bm && saved.bridgeMode) bm.value = saved.bridgeMode;
    const bq = document.getElementById('bridge-query');
    if (bq && saved.bridgeQuery) bq.value = saved.bridgeQuery;
    const bl = document.getElementById('bridge-limit');
    if (bl) bl.value = '0';
    updateBridgeConfig();

    if (saved.wencaiMode) setWencaiMode(saved.wencaiMode, true);
  } catch (_) {}
}

function resetParams() {
  try { localStorage.removeItem(PARAMS_STORE_ID); } catch (_) {}

  setWencaiMode('stock', true);
  _confirmedSectors = [];
  renderConfirmedChips();
  const sq = document.getElementById('sector-query');
  if (sq) sq.value = '';

  applySkillOrder(Object.keys(SKILL_META));
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
  const runScope = document.getElementById('run-scope-limit');
  if (runScope) runScope.value = '500';
  const wq = document.getElementById('wencai-query');
  if (wq) wq.value = '';
  const mc = document.getElementById('manual-codes');
  if (mc) mc.value = '';
  const be = document.getElementById('bridge-enabled');
  if (be) be.checked = false;
  const bm = document.getElementById('bridge-mode');
  if (bm) bm.value = 'constrained';
  const bq = document.getElementById('bridge-query');
  if (bq) bq.value = '';
  const bl = document.getElementById('bridge-limit');
  if (bl) bl.value = '0';
  updateBridgeConfig();
}

// ── 初始化 ────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('/api/skill_catalog');
    if (res.ok) {
      const cat = await res.json();
      SKILL_CATALOG_GRAY = cat.gray || [];
    }
  } catch (_) {}

  buildSkillList();
  initResizers();
  bindSourceToggle();
  bindAllALimitWatch();
  bindWencaiModeButtons();
  bindPresetButtons();
  bindFavButtons();
  bindScanButton();
  bindConfirmSectorsButton();
  bindBridgeControls();
  bindRunScopeControls();
  restoreParams();
  bindResetParams();
  bindRunButton();
  bindAbortButton();
  bindViewReportButton();
  bindClearLogButton();
  bindHelpButtons();
  renderFavBar('wencai-fav-bar', FAV_KEY_WENCAI, applyWencaiFav);
  renderFavBar('sector-fav-bar', FAV_KEY_SECTOR, applySectorFav);
  initRightTabs();
  initPromptLib();
  renderHistory();
  initMgmtCenter();
  checkHealth();
  notifyStrategyStateChanged();
});

// ── 健康检查 ──────────────────────────────────────────────────────────
async function checkHealth() {
  const dot   = $('health-dot');
  const label = $('health-label');
  try {
    const res  = await fetch(API.health);
    const data = await res.json();
    const ok   = data.status === 'ok';
    dot.className     = 'health-dot ' + (ok ? 'ok' : 'err');
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

// ── 技能列表构建 ──────────────────────────────────────────────────────
function buildSkillList() {
  const container = $('skill-list');
  container.innerHTML = '';
  const defaults = new Set(['kline', 'landmine']);

  for (const [id, meta] of Object.entries(SKILL_META)) {
    const item = document.createElement('div');
    item.className = 'skill-item';
    item.dataset.skillId = id;

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

    // 负向标签
    if (meta.semantics === 'negative') {
      const t = document.createElement('span');
      t.className   = 'tag tag-neg';
      t.textContent = '负向';
      lbl.appendChild(document.createTextNode(' '));
      lbl.appendChild(t);
    }

    const moveControls = document.createElement('div');
    moveControls.className = 'skill-move-controls';
    [
      ['up', -1, '↑', '上移'],
      ['down', 1, '↓', '下移'],
    ].forEach(([dir, delta, text, title]) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className   = 'skill-move-btn';
      btn.dataset.move = dir;
      btn.textContent  = text;
      btn.title        = title;
      btn.setAttribute('aria-label', `${meta.label}${title}`);
      btn.addEventListener('click', ev => {
        ev.preventDefault();
        ev.stopPropagation();
        moveSkillItem(id, delta);
      });
      moveControls.appendChild(btn);
    });

    row.appendChild(cb);
    row.appendChild(lbl);
    row.appendChild(moveControls);
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

        const helpEl = document.createElement('span');
        if (pd.help) {
          helpEl.innerHTML = helpButton(pd.help);
        }

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
            if (pd.help) prow.appendChild(helpEl);
            prow.appendChild(inp);
            prow.appendChild(modeWarn);
            inp.id = `p-${id}-${pd.name}`;
            panel.appendChild(prow);
            continue;
          }
        } else {
          inp = document.createElement('input');
          inp.type  = 'number';
          inp.step  = pd.type === 'int' ? '1' : '0.01';
          inp.value = String(pd.default);
          inp.style.cssText = 'width:72px;font-size:11px;padding:3px 6px;';
        }
        inp.id = `p-${id}-${pd.name}`;

        const hint = document.createElement('span');
        hint.textContent = pd.hint;
        hint.style.cssText = 'font-size:10px;color:var(--muted);';

        prow.appendChild(pl);
        if (pd.help) prow.appendChild(helpEl);
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

  // ── 灰色技能折叠区 ─────────────────────────────────────────────────
  const LS_GRAY = 'v6op_v6_assets_collapsed';
  let grayCollapsed = true;
  try {
    const stored = localStorage.getItem(LS_GRAY);
    if (stored !== null) grayCollapsed = (stored === 'true');
  } catch (_) {}

  const graySection = document.createElement('div');
  graySection.className = 'v6-gray-section';

  const grayToggle = document.createElement('div');
  grayToggle.className = 'v6-gray-toggle';
  grayToggle.id = 'v6-gray-toggle';

  const grayBody = document.createElement('div');
  grayBody.className = 'v6-gray-body';
  grayBody.id = 'v6-gray-body';
  if (grayCollapsed) grayBody.classList.add('collapsed');

  function updateGrayToggle() {
    const collapsed = grayBody.classList.contains('collapsed');
    const count = SKILL_CATALOG_GRAY.length;
    grayToggle.innerHTML =
      `<span style="font-size:9px">${collapsed ? '▶' : '▼'}</span>`
      + ` V6 技能资产（暂未接通）`
      + (collapsed && count > 0 ? ` <span class="v6-gray-count">${count}</span>` : '');
  }
  updateGrayToggle();

  grayToggle.addEventListener('click', () => {
    const nowCollapsed = grayBody.classList.toggle('collapsed');
    try { localStorage.setItem(LS_GRAY, String(nowCollapsed)); } catch (_) {}
    updateGrayToggle();
  });

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

    grayBody.appendChild(item);
  }

  graySection.appendChild(grayToggle);
  graySection.appendChild(grayBody);
  container.appendChild(graySection);
  updateSkillMoveButtons();
}

// ── 三栏拖拽调宽 ─────────────────────────────────────────────────────
function initResizers() {
  const layout   = document.querySelector('.console-layout');
  const panels   = Array.from(layout ? layout.querySelectorAll('.panel') : []);
  const rLeft    = document.getElementById('resizer-left');
  const rRight   = document.getElementById('resizer-right');
  if (!rLeft || !rRight || panels.length < 3) return;

  const LS_COLS   = 'v6op_layout_columns';
  const MIN_LEFT  = 160;
  const MIN_MID   = 180;
  const MIN_RIGHT = 160;

  function applyWidths(leftW, rightW) {
    panels[0].style.width    = leftW + 'px';
    panels[0].style.flex     = 'none';
    panels[1].style.flex     = '1 1 0';
    panels[1].style.width    = '';
    panels[1].style.minWidth = MIN_MID + 'px';
    panels[2].style.width    = rightW + 'px';
    panels[2].style.flex     = 'none';
  }

  function saveWidths() {
    const lw = Math.round(panels[0].getBoundingClientRect().width);
    const rw = Math.round(panels[2].getBoundingClientRect().width);
    try { localStorage.setItem(LS_COLS, JSON.stringify([lw, rw])); } catch (_) {}
  }

  let leftW = 260, rightW = 300;
  try {
    const saved = JSON.parse(localStorage.getItem(LS_COLS));
    if (Array.isArray(saved) && saved.length === 2) {
      leftW  = Math.max(MIN_LEFT,  saved[0]);
      rightW = Math.max(MIN_RIGHT, saved[1]);
    }
  } catch (_) {}
  applyWidths(leftW, rightW);

  function makeDrag(resizer, isLeft) {
    resizer.addEventListener('mousedown', e => {
      e.preventDefault();
      const startX = e.clientX;
      const startW = isLeft
        ? panels[0].getBoundingClientRect().width
        : panels[2].getBoundingClientRect().width;
      resizer.classList.add('dragging');
      document.body.style.userSelect = 'none';
      document.body.style.cursor     = 'col-resize';

      function onMove(ev) {
        const dx = ev.clientX - startX;
        if (isLeft) panels[0].style.width = Math.max(MIN_LEFT, startW + dx) + 'px';
        else        panels[2].style.width = Math.max(MIN_RIGHT, startW - dx) + 'px';
      }
      function onUp() {
        resizer.classList.remove('dragging');
        document.body.style.userSelect = '';
        document.body.style.cursor     = '';
        saveWidths();
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup',   onUp);
      }
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup',   onUp);
    });
  }

  makeDrag(rLeft,  true);
  makeDrag(rRight, false);
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

// ── Bridge 二次问财验证 ───────────────────────────────────────────────
function bindBridgeControls() {
  const enabled = $('bridge-enabled');
  const mode    = $('bridge-mode');
  const query   = $('bridge-query');
  const limit   = $('bridge-limit');
  if (enabled) enabled.addEventListener('change', () => {
    updateBridgeConfig();
    saveParams();
  });
  if (mode) mode.addEventListener('change', updateBridgeConfig);
  [mode, query, limit].forEach(el => {
    if (el) el.addEventListener('change', saveParams);
  });
  if (query) query.addEventListener('input', saveParams);
  updateBridgeConfig();
}

function updateBridgeConfig() {
  const enabled = !!$('bridge-enabled')?.checked;
  const config  = $('bridge-config');
  const hint    = $('bridge-hint');
  const mode    = $('bridge-mode')?.value || 'constrained';
  if (config) config.classList.toggle('hidden', !enabled);
  if (hint) {
    hint.textContent = mode === 'annotate'
      ? '标注模式在最终命中后再问财，只增加 in_wencai 标签，不改变命中列表；问财不再按档位截断。'
      : '约束模式在取数前执行问财，并与当前股票池取交集，可能减少后续分析范围；问财不再按档位截断。';
  }
}

// ── 全 A 档位警告联动 ─────────────────────────────────────────────────
function bindAllALimitWatch() {
  const inp = $('all-a-limit');
  if (!inp) return;
  function update() {
    const warnEl     = $('all-a-warn');
    const warnText   = $('all-a-warn-text');
    if (warnEl)   warnEl.classList.remove('hidden');
    if (warnText) warnText.textContent = '全 A 股按本地名单全量读取，不再截断；超过 300 / 500 / 2000 只只做提示，不拦截运行。';
    inp.value = '0';
  }
  inp.addEventListener('change', update);
  update();
}

function bindRunScopeControls() {
  const el = $('run-scope-limit');
  if (!el) return;
  el.addEventListener('change', () => {
    saveParams();
    notifyStrategyStateChanged();
  });
}

// ── 问财模式切换 ──────────────────────────────────────────────────────
function bindWencaiModeButtons() {
  const btnStock  = $('wm-btn-stock');
  const btnSector = $('wm-btn-sector');
  if (btnStock)  btnStock.addEventListener('click',  () => setWencaiMode('stock'));
  if (btnSector) btnSector.addEventListener('click', () => setWencaiMode('sector'));
}

function setWencaiMode(mode, silent = false) {
  _wencaiMode = mode;
  const phaseA  = $('phase-a-panel');
  const phaseB  = $('phase-b-label');
  const btnS    = $('wm-btn-stock');
  const btnSec  = $('wm-btn-sector');
  if (phaseA) phaseA.classList.toggle('hidden', mode !== 'sector');
  if (phaseB) phaseB.textContent = mode === 'sector' ? 'Phase B — 问财个股选股' : '问财选股语句';
  if (btnS)   btnS.classList.toggle('active',  mode === 'stock');
  if (btnSec) btnSec.classList.toggle('active', mode === 'sector');
  if (!silent) saveParams();
  notifyStrategyStateChanged();
}

// ── P1-P6 预设 ────────────────────────────────────────────────────────
function bindPresetButtons() {
  document.querySelectorAll('.preset-btn[data-preset]').forEach(btn => {
    btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
  });
}

function applyPreset(key) {
  const query = PRESET_QUERIES[key];
  if (!query) return;
  // 切到问财来源
  const wencaiRadio = document.querySelector('input[name="source-type"][value="wencai"]');
  if (wencaiRadio && !wencaiRadio.checked) {
    wencaiRadio.checked = true;
    wencaiRadio.dispatchEvent(new Event('change'));
  }
  // 切到个股模式
  setWencaiMode('stock');
  // 填入
  const wq = $('wencai-query');
  if (wq) {
    wq.value = query;
    wq.focus();
    wq.dispatchEvent(new Event('input', { bubbles: true }));
    wq.dispatchEvent(new Event('change', { bubbles: true }));
  }
  saveParams();
  notifyStrategyStateChanged();
}

// ── 收藏 CRUD ─────────────────────────────────────────────────────────
function loadFavs(key) {
  try { return JSON.parse(localStorage.getItem(key) || '[]'); }
  catch (_) { return []; }
}

function saveFavs(key, favs) {
  try { localStorage.setItem(key, JSON.stringify(favs)); } catch (_) {}
}

function addFav(key, query) {
  if (!query.trim()) return;
  const favs = loadFavs(key);
  if (favs.some(f => f.query === query)) return;
  const label = query.length > 18 ? query.slice(0, 18) + '…' : query;
  favs.unshift({ label, query });
  if (favs.length > 20) favs.pop();
  saveFavs(key, favs);
}

function renderFavBar(containerId, key, onSelectFn) {
  const container = $(containerId);
  if (!container) return;
  const favs = loadFavs(key);
  if (!favs.length) { container.innerHTML = ''; return; }
  container.innerHTML = favs.map((f, i) =>
    `<span class="fav-chip">`
    + `<span class="fav-chip-label" title="${esc(f.query)}" `
    + `onclick="window._applyFav(${JSON.stringify(key)},${i})">${esc(f.label)}</span>`
    + `<span class="fav-chip-del" title="删除" `
    + `onclick="window._deleteFav(${JSON.stringify(key)},${i})">×</span>`
    + `</span>`
  ).join('');
}

// 全局回调（HTML inline onclick 需要 window scope）
window._applyFav = function(key, idx) {
  const favs = loadFavs(key);
  if (!favs[idx]) return;
  if (key === FAV_KEY_WENCAI) applyWencaiFav(favs[idx].query);
  else if (key === FAV_KEY_SECTOR) applySectorFav(favs[idx].query);
};

window._deleteFav = function(key, idx) {
  const favs = loadFavs(key);
  favs.splice(idx, 1);
  saveFavs(key, favs);
  if (key === FAV_KEY_WENCAI) renderFavBar('wencai-fav-bar', key, applyWencaiFav);
  else if (key === FAV_KEY_SECTOR) renderFavBar('sector-fav-bar', key, applySectorFav);
};

function applyWencaiFav(query) {
  const wq = $('wencai-query');
  if (wq) {
    wq.value = query;
    wq.dispatchEvent(new Event('input', { bubbles: true }));
    wq.dispatchEvent(new Event('change', { bubbles: true }));
  }
  saveParams();
  notifyStrategyStateChanged();
}

function applySectorFav(query) {
  const sq = $('sector-query');
  if (sq) {
    sq.value = query;
    sq.dispatchEvent(new Event('input', { bubbles: true }));
    sq.dispatchEvent(new Event('change', { bubbles: true }));
  }
  saveParams();
  notifyStrategyStateChanged();
}

function bindFavButtons() {
  const btnW = $('btn-save-wencai-fav');
  if (btnW) btnW.addEventListener('click', () => {
    const q = $('wencai-query')?.value.trim();
    if (!q) { showAlert('center-alerts', 'warn', '问财语句为空，无法收藏'); return; }
    addFav(FAV_KEY_WENCAI, q);
    renderFavBar('wencai-fav-bar', FAV_KEY_WENCAI, applyWencaiFav);
  });

  const btnS = $('btn-save-sector-fav');
  if (btnS) btnS.addEventListener('click', () => {
    const q = $('sector-query')?.value.trim();
    if (!q) { showAlert('center-alerts', 'warn', '板块语句为空，无法收藏'); return; }
    addFav(FAV_KEY_SECTOR, q);
    renderFavBar('sector-fav-bar', FAV_KEY_SECTOR, applySectorFav);
  });
}

// ── Phase A 板块扫描 ──────────────────────────────────────────────────
function bindScanButton() {
  const btn = $('btn-scan');
  if (btn) btn.addEventListener('click', scanSectors);
}

async function scanSectors() {
  const sectorQuery = $('sector-query')?.value.trim() || '';
  const topN = parseInt($('sector-top-n')?.value || '10', 10);

  const spinner  = $('scan-spinner');
  const btn      = $('btn-scan');
  const checklist = $('sector-checklist');
  const confirmRow = $('sector-confirm-row');

  if (spinner) spinner.classList.remove('hidden');
  if (btn)     btn.disabled = true;

  try {
    const res = await fetch(API.scanSectors, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ sector_query: sectorQuery, sector_top_n: topN }),
    });
    const data = await res.json();

    if (data.error || !data.sectors || data.sectors.length === 0) {
      const errMsg = data.error || '板块扫描无结果，请调整查询语句';
      if (checklist) {
        checklist.classList.remove('hidden');
        checklist.innerHTML = `<div class="alert alert-warn"><span class="alert-icon">⚠️</span><span>${esc(errMsg)}</span></div>`;
      }
      if (confirmRow) confirmRow.classList.add('hidden');
      return;
    }

    renderSectorChecklist(data.sectors);

  } catch (e) {
    if (checklist) {
      checklist.classList.remove('hidden');
      checklist.innerHTML = `<div class="alert alert-danger"><span class="alert-icon">❌</span><span>扫描请求失败: ${esc(e.message)}</span></div>`;
    }
  } finally {
    if (spinner) spinner.classList.add('hidden');
    if (btn)     btn.disabled = false;
  }
}

function renderSectorChecklist(sectors) {
  const checklist  = $('sector-checklist');
  const confirmRow = $('sector-confirm-row');
  if (!checklist) return;

  checklist.classList.remove('hidden');
  checklist.innerHTML =
    `<div class="sector-checklist-title">扫描到 ${sectors.length} 个板块，请勾选：</div>`
    + `<div class="sector-check-group">`
    + sectors.map((s, i) =>
        `<label class="sector-check-item">`
        + `<input type="checkbox" class="sector-chk" value="${esc(s)}" checked />`
        + ` ${esc(s)}`
        + `</label>`
      ).join('')
    + `</div>`;

  if (confirmRow) confirmRow.classList.remove('hidden');
}

function bindConfirmSectorsButton() {
  const btn = $('btn-confirm-sectors');
  if (btn) btn.addEventListener('click', confirmSectors);
}

function confirmSectors() {
  const checked = Array.from(document.querySelectorAll('.sector-chk:checked'))
    .map(cb => cb.value)
    .filter(Boolean);

  if (!checked.length) {
    showAlert('center-alerts', 'warn', '请至少勾选一个板块');
    return;
  }

  _confirmedSectors = checked;
  renderConfirmedChips();

  // 收起 checklist
  const checklist  = $('sector-checklist');
  const confirmRow = $('sector-confirm-row');
  if (checklist)  checklist.classList.add('hidden');
  if (confirmRow) confirmRow.classList.add('hidden');

  saveParams();
  notifyStrategyStateChanged();
}

function renderConfirmedChips() {
  const container = $('sector-confirmed');
  if (!container) return;
  if (!_confirmedSectors.length) {
    container.style.display = 'none';
    container.innerHTML = '';
    return;
  }
  container.style.display = 'flex';
  container.innerHTML =
    `<span style="font-size:11px;color:var(--muted);margin-right:4px">已确认：</span>`
    + _confirmedSectors.map(s =>
        `<span class="confirmed-chip">${esc(s)}</span>`
      ).join('')
    + `<span class="fav-chip-del" style="margin-left:6px" title="清除已确认板块" onclick="clearConfirmedSectors()">清除</span>`;
}

window.clearConfirmedSectors = function() {
  _confirmedSectors = [];
  renderConfirmedChips();
  saveParams();
  notifyStrategyStateChanged();
};

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
    source.limit = 0;

  } else if (sourceType === 'wencai') {
    let query;

    if (_wencaiMode === 'sector') {
      if (!_confirmedSectors.length) {
        throw new Error('板块联动：请先扫描并确认板块（Phase A）');
      }
      const phaseB = $('wencai-query')?.value.trim();
      if (!phaseB) throw new Error('板块联动：请输入 Phase B 问财个股选股语句');
      const sectorClause = _confirmedSectors
        .map(s => `${s}板块`)
        .join('或');
      query = `属于${sectorClause}，且${phaseB}`;
      // 附带 metadata 便于报告调试（source_resolver 会忽略这些额外字段）
      source.sector_linkage = {
        enabled:           true,
        confirmed_sectors: [..._confirmedSectors],
        phase_a_query:     $('sector-query')?.value.trim() || '',
        phase_b_query:     phaseB,
      };
    } else {
      query = $('wencai-query')?.value.trim();
      if (!query) throw new Error('问财来源：请输入选股语句');
    }

    source.query = query;
    source.limit = 0;
  }

  const skills = [];
  document.querySelectorAll('#skill-list input[type=checkbox]:checked').forEach(cb => {
    if (LIVE_SKILL_IDS.has(cb.value)) skills.push(cb.value);
  });
  if (skills.length === 0) throw new Error('请至少选择一项技能');

  const pathType = document.querySelector('input[name="path-type"]:checked').value;
  let bridge = null;
  if ($('bridge-enabled')?.checked) {
    const bridgeQuery = $('bridge-query')?.value.trim() || '';
    if (!bridgeQuery) throw new Error('Bridge 已启用：请输入二次问财验证语句');
    bridge = {
      mode: $('bridge-mode')?.value || 'constrained',
      wencai_query: bridgeQuery,
      wencai_limit: 0,
    };
  }

  const skillParams = {};
  for (const skillId of skills) {
    const defs = SKILL_PARAMS[skillId] || [];
    if (defs.length === 0) continue;
    const sp = {};
    for (const pd of defs) {
      const el = $(`p-${skillId}-${pd.name}`);
      if (!el) continue;
      let val;
      if (pd.type === 'int')        val = parseInt(el.value, 10);
      else if (pd.type === 'float') val = parseFloat(el.value);
      else if (pd.type === 'bool')  val = el.value === 'true';
      else                          val = el.value;
      if (!isNaN(val) || typeof val === 'string') sp[pd.name] = val;
    }
    if (Object.keys(sp).length > 0) skillParams[skillId] = sp;
  }

  const strategy = {
    source,
    skills,
    path_type: pathType,
    run_scope_limit: getRunScopeLimit(),
    params: { skills: skillParams },
  };
  if (bridge) strategy.bridge = bridge;
  return strategy;
}

// ── 恢复默认参数按钮 ──────────────────────────────────────────────────
function bindResetParams() {
  const btn = $('btn-reset-params');
  if (btn) btn.onclick = () => resetParams();
}

// ── 启动管道按钮 ──────────────────────────────────────────────────────
function bindRunButton() {
  const btn = $('btn-run');
  if (!btn) return;
  btn.onclick = async () => {
    let strategy;
    try {
      strategy = buildStrategy();
    } catch (e) {
      showAlert('center-alerts', 'danger', e.message);
      return;
    }
    saveParams();

    clearResult();
    resetRunPollingState();
    logClear();

    setRunningState(true);
    const srcLabel = strategy.source.type === 'wencai' && strategy.source.sector_linkage
      ? `wencai(板块联动: ${strategy.source.sector_linkage.confirmed_sectors.join('、')})`
      : strategy.source.type;
    logLine('HEAD', `启动管道: 来源=${srcLabel}  技能=[${strategy.skills.join(',')}]  路径=${strategy.path_type}`);
    if (strategy.source.query) {
      logLine('INFO', `问财语句: ${strategy.source.query.slice(0, 80)}${strategy.source.query.length > 80 ? '…' : ''}`);
    }

    try {
      const res = await fetch(API.run, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(strategy),
      });
      if (res.status === 409) {
        const errData = await res.json().catch(() => ({}));
        showAlert('center-alerts', 'warn', errData.error || '已有任务正在运行，请稍候…');
        setRunningState(false);
        return;
      }
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        showAlert('center-alerts', 'danger', errData.error || `启动失败（HTTP ${res.status}）`);
        setRunningState(false);
        setStatus('error');
        return;
      }
      const data = await res.json();
      $('run-id').textContent = data.run_id || '';
      logLine('INFO', `run_id=${data.run_id}  状态=${data.status}`);
      startPoll();
    } catch (e) {
      showAlert('center-alerts', 'danger', `启动失败: ${e.message}`);
      setRunningState(false);
      setStatus('error');
    }
  };
}

// ── 中止运行按钮 ──────────────────────────────────────────────────────
function bindAbortButton() {
  ['btn-abort', 'btn-force-stop'].forEach(id => {
    const btn = $(id);
    if (!btn) return;
    btn.onclick = ev => {
      if (ev) {
        ev.preventDefault();
        ev.stopPropagation();
      }
      forceStopRun();
    };
  });
}

async function forceStopRun() {
  stopPoll();
  setRunningState(false);
  setStatus('aborting');
  logLine('WARN', '已停止页面轮询，并向后端发送中止请求…');
  try {
    const res  = await fetch(API.abort, { method: 'POST' });
    const data = await res.json().catch(() => ({}));
    logLine('WARN', data.message || '中止请求已发送');
    setStatus(data.aborted ? 'aborting' : (data.status || 'idle'));
  } catch (e) {
    logLine('ERROR', `中止请求失败: ${e.message}`);
    setStatus('error');
  }
}

// ── 查看当前报告 ──────────────────────────────────────────────────────
function bindViewReportButton() {
  const btn = $('btn-view-report');
  if (btn) btn.onclick = () => window.open(API.result, '_blank');
}

// ── 清空屏幕日志 ──────────────────────────────────────────────────────
function bindClearLogButton() {
  const btn = $('btn-clear-log');
  if (btn) btn.onclick = () => { logClear(); logLine('INFO', '屏幕日志已清空（磁盘文件未删除）'); };
}

function bindHelpButtons() {
  document.addEventListener('click', ev => {
    const btn = ev.target && ev.target.closest ? ev.target.closest('.info-btn') : null;
    if (!btn) return;
    const helpKey = btn.dataset.help;
    if (helpKey) showHelp(helpKey);
  });
  document.addEventListener('keydown', ev => {
    if (ev.key === 'Escape') closeHelp();
  });
}

function helpButton(helpKey, label = 'i') {
  return `<button class="info-btn" type="button" data-help="${esc(helpKey)}" aria-label="查看说明">${esc(label)}</button>`;
}

function showHelp(helpKey) {
  const item = HELP_TEXT[helpKey];
  if (!item) return;
  let overlay = $('help-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'help-overlay';
    overlay.className = 'help-overlay hidden';
    overlay.innerHTML = `
      <div class="help-popover" role="dialog" aria-modal="true" aria-labelledby="help-title">
        <button class="help-close" type="button" aria-label="关闭说明">×</button>
        <div id="help-title" class="help-title"></div>
        <div id="help-body" class="help-body"></div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', ev => {
      if (ev.target === overlay || ev.target.closest('.help-close')) closeHelp();
    });
  }
  const title = $('help-title');
  const body = $('help-body');
  if (title) title.textContent = item.title;
  if (body) {
    body.innerHTML = (item.body || []).map(text =>
      `<p>${esc(text)}</p>`
    ).join('');
  }
  overlay.classList.remove('hidden');
}

function closeHelp() {
  const overlay = $('help-overlay');
  if (overlay) overlay.classList.add('hidden');
}

// ── 轮询 /api/stream ──────────────────────────────────────────────────
function startPoll() {
  stopPoll();
  _pollTimer = setInterval(pollStream, 1500);
}
function stopPoll() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

function resetRunPollingState() {
  stopPoll();
  _lastEventCount = 0;
  _resultFetchedForRunId = null;
}

async function pollStream() {
  try {
    const res  = await fetch(`${API.stream}?since=${_lastEventCount}`);
    const data = await res.json();

    setStatus(data.status || 'idle');
    if (data.run_id) $('run-id').textContent = data.run_id;

    const newEvents = data.events || [];
    newEvents.forEach(ev => logLine(ev.level, ev.msg));
    if (data.event_count != null) _lastEventCount = data.event_count;

    const terminal = ['completed', 'error', 'aborted'];
    if (terminal.includes(data.status)) {
      stopPoll();
      setRunningState(false);
      const runKey = data.run_id || 'current';
      if (_resultFetchedForRunId !== runKey) {
        _resultFetchedForRunId = runKey;
        await fetchResult();
      }
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
  renderRunFailureNotice(r);

  // 保存到历史 + 更新提示词库状态
  saveRunToHistory(r);
  fillPromptFromLastResult(r);
  renderPromptText();

  renderCoverage(r);
  renderPrefetch(r);
  renderReadiness(r);
  renderWarnings(r);
  renderProducers(r);
  renderHits(r);
  renderFailed(r);
  renderReportLinks(r);
  renderGlobalExplanation(r);
  renderDataProvenance(r);
  renderBridgeResult(r);
}

function diagnoseRunFailure(r) {
  if (!r || r.status !== 'error') return '';
  const source = ((r.strategy_snapshot || {}).source) || ((r.strategy || {}).source) || {};
  const scope = r.scope || {};
  const sourceType = source.type || scope.source_type || ((r.source_info || {}).source_type) || '';
  const scopeCount = Number((r.data_coverage || {}).scope_count ?? scope.scope_count ?? 0);
  const rawError = r.error || scope.error || '';
  const query = source.query || (r.source_info || {}).query_text || scope.query_text || '';

  if (sourceType === 'wencai' && scopeCount === 0) {
    const queryTip = query ? ` 当前问财语句：${String(query).slice(0, 90)}` : '';
    return `问财来源没有形成股票池，后续技能没有输入。请先检查问财接口/session 是否正常，或换一句最基础问财语句验证接口。${queryTip}`;
  }
  if (String(rawError).includes('scope 为空')) {
    return '股票池为空，后续技能没有输入。请先检查股票来源、问财语句或 Bridge 条件。';
  }
  return rawError ? `运行失败：${rawError}` : '运行失败：请查看下方运行日志和 run_report.json。';
}

function renderRunFailureNotice(r) {
  const el = $('center-alerts');
  if (!el) return;
  el.querySelectorAll('.run-failure-alert').forEach(node => node.remove());
  const message = diagnoseRunFailure(r);
  if (!message) return;
  const failureKey = `${r.run_id || ''}|${message}`;
  if (el.dataset.runFailureKey === failureKey) return;
  el.dataset.runFailureKey = failureKey;
  const div = document.createElement('div');
  div.className = 'alert alert-danger run-failure-alert';
  div.innerHTML = `<span class="alert-icon">!</span><span>${esc(message)}</span>`;
  el.appendChild(div);
  logLine('ERROR', message);
}

function renderPrefetch(r) {
  const el = $('prefetch-box');
  if (!el) return;
  const triggered = r.prefetch_triggered;
  const pr = triggered ? (r.prefetch_report || {}) : null;

  if (!triggered || !pr || Object.keys(pr).length === 0) {
    el.innerHTML = '<div class="storage-note storage-note-kline">'
      + '<span class="storage-stars">★★</span>'
      + '<span><b>K线数据库已够用</b>：本轮没有重新访问行情源，直接读取本机已保存的K线。</span>'
      + helpButton('kline-db')
      + '</div>';
    return;
  }

  const dtm = pr.data_time_max ? String(pr.data_time_max).slice(0, 10) : null;
  let staleDays = '—', staleNote = '';
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
    ['★★ 已在K线库',  pr.cache_hit       ?? '—', 'text-green'],
    ['★★ 本次新取K线', pr.fetched_ok      ?? '—', 'text-green'],
    ['★★ 备用源补回',  pr.recovered_count ?? 0,   'text-green'],
    ['取数失败',     pr.failed          ?? '—', 'text-red'],
    ['使用旧K线',    pr.stale_used      ?? '—', 'text-yellow'],
    ['K线最新日期', dtm || '—',                ''],
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
    aborted: { cls: 'alert-danger', icon: '⛔', text: `数据状态：中止（aborted）  取数失败率 ${pct(dc.failure_rate)}，结果不可信` },
    partial:  { cls: 'alert-warn',  icon: '⚠️', text: `数据状态：部分可分析（partial）  部分K线缺失，结果仅供参考` },
    ready:    { cls: 'alert-ok',    icon: '✅', text: `数据状态：可分析（ready）  本轮数据充足` },
  };
  const t = types[readiness] || { cls: 'alert-info', icon: 'ℹ️', text: `数据状态：${readiness}` };
  const div = document.createElement('div');
  div.className = `alert ${t.cls}`;
  div.innerHTML = `<span class="alert-icon">${t.icon}</span><span>${t.text}</span>`;
  el.appendChild(div);
}

function renderCoverage(r) {
  const dc = r.data_coverage || {};
  const sourceCfg = ((r.strategy || {}).source || {});
  const runScope = r.run_scope || ((r.strategy_snapshot || {}).run_scope) || {};
  const sourceType = sourceCfg.type || ((r.scope || {}).source_type) || ((r.scope || {}).source) || 'source';
  const sourceLabel = sourceType === 'wencai'
    ? '问财来源快照'
    : sourceType === 'all_a'
      ? 'A股来源快照'
      : sourceType === 'manual'
        ? '手输来源快照'
        : '来源快照';
  const sourceCount = dc.scope_count ?? ((r.scope || {}).scope_count);
  const sourceOriginalCount = runScope.original_scope_count ?? dc.source_original_count ?? sourceCount;
  const runScopeLimit = Number(runScope.limit ?? dc.run_scope_limit ?? 0);
  const runScopeSuffix = runScopeLimit > 0
    ? `；运行规模 测试 ${runScopeLimit}，原始池 ${sourceOriginalCount ?? '-'} 只`
    : '；运行规模 全量';
  const sourceLimit = Number(sourceCfg.limit || 0);
  const sourceHint = sourceType === 'wencai' && sourceLimit
    ? `问财实际返回 ${sourceCount ?? '-'} / 档位上限 ${sourceLimit}`
    : sourceType === 'all_a' && sourceLimit
      ? `本地A股取用 ${sourceCount ?? '-'} / 档位上限 ${sourceLimit}`
      : sourceType === 'manual'
        ? `手输名单 ${sourceCount ?? '-'} 只`
        : '本轮股票池，会被下一轮运行覆盖';
  const skillHits = r.mask_cache_hits ?? 0;
  const skillMisses = r.mask_cache_misses ?? 0;
  $('coverage-box').innerHTML = `
    <div class="storage-legend">
      <div class="storage-card storage-card-source">
        <span class="storage-stars">★</span>
        <div class="storage-copy">
          <b>${esc(sourceLabel)} ${helpButton('source-snapshot')}</b>
          <span>${esc(sourceHint + runScopeSuffix)}</span>
        </div>
        <span class="storage-count">${sourceCount ?? '-'}</span>
      </div>
      <div class="storage-card storage-card-kline">
        <span class="storage-stars">★★</span>
        <div class="storage-copy">
          <b>K线数据库 ${helpButton('kline-db')}</b>
          <span>已保存到本机，重启后仍可复用</span>
        </div>
        <span class="storage-count">${dc.cached_count ?? '-'}</span>
      </div>
      <div class="storage-card storage-card-mask">
        <span class="storage-stars">★★★</span>
        <div class="storage-copy">
          <b>技能结果库 ${helpButton('skill-result-store')}</b>
          <span>同股票池、同参数、同日期才复用</span>
        </div>
        <span class="storage-count">${skillHits}/${skillHits + skillMisses}</span>
      </div>
    </div>
    <div class="coverage-grid">
      <div class="cov-item"><span class="cov-label">来源总数</span><span class="cov-value">${dc.scope_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">运行规模</span><span class="cov-value">${runScopeLimit > 0 ? `测试 ${runScopeLimit}` : '全量'}</span></div>
      <div class="cov-item"><span class="cov-label">本地K线可用</span><span class="cov-value text-green">${dc.cached_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">缺K线数据</span><span class="cov-value text-yellow">${dc.missing_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">取数失败</span><span class="cov-value text-red">${dc.failed_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">旧K线</span><span class="cov-value text-yellow">${dc.stale_count ?? '-'}</span></div>
      <div class="cov-item"><span class="cov-label">取数失败率</span><span class="cov-value">${pct(dc.failure_rate)}</span></div>
    </div>`;
}

function renderWarnings(r) {
  const warnings   = r.warnings || [];
  const exprMeta   = (r.expression || {}).metadata || {};
  const softFilters = exprMeta.soft_filter_skills || [];
  const weakSignals = exprMeta.weak_signal_skills || [];

  const extra = [];
  if (softFilters.length)
    extra.push(`⚠ SMC soft_filter 模式（${softFilters.join(',')}）：结果为软过滤/透传，非 strict 正向命中`);
  if (weakSignals.length)
    extra.push(`⚠ 波浪放行（${weakSignals.join(',')}）：no_top 只是"没发现5浪顶部"，不应视为强买入信号`);

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
    (h.skill_hits || []).forEach(s => {
      if (softFilters.has(s.skill_id))
        tags.push(`<span class="tag tag-debug">${esc(s.skill_name)}</span>`);
      else
        tags.push(`<span class="tag" style="background:#1e3a5f;color:#93c5fd">${esc(s.skill_name)}</span>`);
    });

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
    stEl.innerHTML = '<b>旧K线：</b>' + stale.map(c => esc(c)).join(', ');
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
    aborting:  ['badge-aborted',   '停止中'],
    completed: ['badge-completed', '完成'],
    error:     ['badge-error',     '错误'],
    aborted:   ['badge-aborted',   '已中止'],
  };
  const [cls, text] = map[status] || ['badge-idle', status];
  _currentRunStatus = status || 'idle';
  el.className   = `badge ${cls}`;
  el.textContent = text;
}

function setRunningState(isRunning) {
  const runBtn   = $('btn-run');
  const abortBtn = $('btn-abort');
  const forceBtn = $('btn-force-stop');
  const spinner  = $('run-spinner');
  document.body.classList.toggle('v6op-running', !!isRunning);
  if (runBtn)   runBtn.disabled   = isRunning;
  if (abortBtn) abortBtn.disabled = !isRunning;
  if (forceBtn) {
    forceBtn.disabled = false;
    forceBtn.textContent = isRunning ? '强制停止' : '停止刷新';
  }
  if (spinner) {
    if (isRunning) spinner.classList.remove('hidden');
    else           spinner.classList.add('hidden');
  }
  if (isRunning) {
    const logDetails = $('log-details');
    if (logDetails) logDetails.open = true;
    const centerPanel = document.querySelector('.strategy-center-panel');
    if (centerPanel) centerPanel.scrollTop = 0;
    const logBox = $('log-box');
    if (logBox) logBox.scrollTop = logBox.scrollHeight;
  }
  if (isRunning) {
    setStatus('pending');
  } else if (['pending', 'running', 'aborting'].includes(_currentRunStatus)) {
    setStatus('idle');
  }
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
  const alerts = $('center-alerts');
  if (alerts) {
    alerts.innerHTML = '';
    delete alerts.dataset.runFailureKey;
  }
  const explSection = $('global-explanation-section');
  if (explSection) explSection.classList.add('hidden');
  const provSection = $('data-provenance-section');
  if (provSection) provSection.classList.add('hidden');
  const bridgeSection = $('bridge-result-section');
  if (bridgeSection) bridgeSection.classList.add('hidden');
  const badge = $('why-zero-badge');
  if (badge) badge.classList.add('hidden');
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
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;');
}

function pct(v) {
  if (v == null) return '—';
  return (v * 100).toFixed(1) + '%';
}

// ══════════════════════════════════════════════════════════════════
// 右侧三标签
// ══════════════════════════════════════════════════════════════════

function initRightTabs() {
  const tabs   = document.querySelectorAll('.rtab');
  const panels = document.querySelectorAll('.rtab-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('rtab-active'));
      panels.forEach(p => p.classList.add('rtab-panel-hidden'));
      tab.classList.add('rtab-active');
      const target = document.getElementById('rtab-' + tab.dataset.rtab);
      if (target) target.classList.remove('rtab-panel-hidden');
      if (tab.dataset.rtab === 'history') renderHistory();
    });
  });
}

// ══════════════════════════════════════════════════════════════════
// 提示词库
// ══════════════════════════════════════════════════════════════════

const LS_CUSTOM_PROMPT = 'v6op_custom_prompt';
const LS_RUN_HISTORY   = 'v6op_run_history';

const PROMPT_TEMPLATES = {
  '综合分析': `你是一位资深 A 股研究员。以下是今日量化筛选结果：

✅ 精选股票：{{股票列表}}
📋 选股策略：{{选股策略}}
🔀 分析路径：{{执行路径}}

请对以上股票进行综合技术面分析：
1. 当前位置判断（区间震荡 / 突破启动 / 趋势延续 / 拐点疑似）
2. 各股技术结构优劣对比，横向排序
3. 操作优先级推荐（最多 3 只并说明理由）
4. 值得关注的风险点（关键支撑、压力、可能破坏结构的信号）`,

  '风险管理': `以下股票通过了技术面量化筛选，请站在风险管理视角评估：

✅ 精选股票：{{股票列表}}
📋 选股策略：{{选股策略}}

请分析：
1. 关键支撑位和压力位（均线、前高前低、缺口区间）
2. 当前建仓的主要风险点
3. SMC 结构中是否存在未验证的 BOS / ChoCH
4. 各股止损位建议（技术面破坏信号描述）
5. 建议仓位控制比例（轻仓 / 正常 / 分批）`,

  '板块验证': `以下股票已通过个股筛选，请验证其板块联动性：

✅ 精选股票：{{股票列表}}
📋 选股策略：{{选股策略}}

请分析：
1. 这些股票分别属于哪些板块 / 概念 / 行业
2. 近期板块资金流向（主力净流入 / 净流出）
3. 相关板块处于哪个阶段（启动 / 强势 / 退潮）
4. 板块联动效应最强的 1-2 只，优先关注理由`,

  '资金分析': `请对以下精选股票进行主力资金行为深度分析：

✅ 精选股票：{{股票列表}}

请尽可能详尽说明：
1. 近 5 日大单净流入 / 净流出及趋势变化
2. 主力参与迹象（筹码集中度、换手率异常、封板行为）
3. 量价配合是否理想（放量上涨 / 缩量突破 / 放量滞涨）
4. 综合判断：资金是否在建仓 / 出货 / 观望阶段`,

  '交易计划': `请为以下精选股票制定具体可执行的交易计划：

✅ 精选股票：{{股票列表}}
📋 选股策略：{{选股策略}}
🔀 分析路径：{{执行路径}}

请分别制定：
1. 买入时机：具体触发条件（突破什么价位 / 回踩什么支撑）
2. 目标价：第一目标 / 第二目标（以技术面依据说明）
3. 止损位：明确价格或破位条件
4. 持仓周期预判：短线（3-5 日）/ 中线（1-3 周）/ 趋势
5. 风险收益比评估`,

  '快速输出': `请用每只股票不超过 3 句话的极简格式给出买入摘要：

✅ 精选股票：{{股票列表}}

格式：
【股票代码/名称】
· 技术面：[一句话判断]
· 操作建议：[一句话]
· 风险提示：[一句话]`,

  '自定义': '',
};

let _currentPtab    = '综合分析';
let _promptFillData = { stocks: '', strategy: '', path: '' };

function initPromptLib() {
  // 读取已保存的自定义提示词
  try {
    const saved = localStorage.getItem(LS_CUSTOM_PROMPT);
    if (saved) PROMPT_TEMPLATES['自定义'] = saved;
  } catch (_) {}

  // 内层标签切换
  document.querySelectorAll('.ptab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.ptab').forEach(t => t.classList.remove('ptab-active'));
      tab.classList.add('ptab-active');
      _currentPtab = tab.dataset.ptab;
      renderPromptText();
      const saveBtn = document.getElementById('btn-save-custom');
      if (saveBtn) saveBtn.style.display = (_currentPtab === '自定义') ? '' : 'none';
    });
  });

  // 初始渲染
  renderPromptText();

  // 同步按钮
  const fillBtn = document.getElementById('btn-prompt-fill');
  if (fillBtn) fillBtn.addEventListener('click', () => {
    fillPromptFromLastResult();
    renderPromptText();
  });

  // 复制按钮
  const copyBtn = document.getElementById('btn-copy-prompt');
  if (copyBtn) copyBtn.addEventListener('click', () => {
    const ta = document.getElementById('prompt-text');
    if (!ta) return;
    navigator.clipboard.writeText(ta.value).then(() => {
      const tip = document.getElementById('copy-tip');
      if (!tip) return;
      tip.style.display = '';
      setTimeout(() => { tip.style.display = 'none'; }, 2000);
    }).catch(() => {
      ta.select();
      document.execCommand('copy');
    });
  });

  // 保存自定义
  const saveBtn = document.getElementById('btn-save-custom');
  if (saveBtn) saveBtn.addEventListener('click', () => {
    const ta = document.getElementById('prompt-text');
    if (!ta) return;
    PROMPT_TEMPLATES['自定义'] = ta.value;
    try { localStorage.setItem(LS_CUSTOM_PROMPT, ta.value); } catch (_) {}
    saveBtn.textContent = '✅ 已保存';
    setTimeout(() => { saveBtn.textContent = '💾 保存自定义'; }, 1500);
  });

  // 手动编辑提示词时同步到自定义模板（仅自定义标签）
  const ta = document.getElementById('prompt-text');
  if (ta) ta.addEventListener('input', () => {
    if (_currentPtab === '自定义') PROMPT_TEMPLATES['自定义'] = ta.value;
  });
}

function renderPromptText() {
  const ta = document.getElementById('prompt-text');
  if (!ta) return;
  let tpl = PROMPT_TEMPLATES[_currentPtab] || '';
  if (_promptFillData.stocks) {
    tpl = tpl
      .replace(/\{\{股票列表\}\}/g,  _promptFillData.stocks)
      .replace(/\{\{选股策略\}\}/g,  _promptFillData.strategy)
      .replace(/\{\{执行路径\}\}/g,  _promptFillData.path);
  }
  ta.value = tpl;
}

function fillPromptFromLastResult(r) {
  const src = r || _lastResult;
  if (!src) return;

  const codes = (src.final_hit_codes || []).join(', ') || '（本轮无命中）';
  const ss    = src.source_summary || {};
  let strategy = '';
  if (ss.source_type === 'wencai' && ss.query) {
    strategy = ss.query;
  } else if (ss.source_type === 'all_a') {
    strategy = '全 A 股扫描（' + (ss.limit || '') + '）';
  } else if (ss.source_type === 'manual') {
    strategy = '手动输入';
  } else {
    strategy = ss.source_type || '未知来源';
  }
  const pathMap = { sequential: '顺序漏斗', parallel_and: '并行取交集', simple_hybrid: '简单混合' };
  const path    = pathMap[src.execution_path] || src.execution_path || '—';

  _promptFillData = { stocks: codes, strategy, path };

  const statusEl = document.getElementById('prompt-fill-status');
  if (statusEl) {
    const hitN = (src.final_hit_codes || []).length;
    statusEl.textContent = `已同步：${hitN} 只命中，run_id: ${(src.run_id || '').slice(-8)}`;
    statusEl.style.color = 'var(--green)';
  }
}

// ══════════════════════════════════════════════════════════════════
// 历史报告
// ══════════════════════════════════════════════════════════════════

function saveRunToHistory(r) {
  if (!r || !r.run_id) return;
  try {
    const hist = JSON.parse(localStorage.getItem(LS_RUN_HISTORY) || '[]');
    const ss   = r.source_summary || {};
    const entry = {
      run_id:      r.run_id,
      time:        r.generated_at || new Date().toISOString(),
      hit_count:   (r.final_hit_codes || []).length,
      scope_count: ss.scope_count || ss.limit || '?',
      source_type: ss.source_type || '?',
      query:       ss.query || '',
      final_codes: r.final_hit_codes || [],
    };
    const filtered = hist.filter(h => h.run_id !== r.run_id);
    filtered.unshift(entry);
    if (filtered.length > 20) filtered.length = 20;
    localStorage.setItem(LS_RUN_HISTORY, JSON.stringify(filtered));
  } catch (_) {}
}

function renderHistory() {
  const el = document.getElementById('history-list');
  if (!el) return;
  let hist = [];
  try { hist = JSON.parse(localStorage.getItem(LS_RUN_HISTORY) || '[]'); } catch (_) {}

  if (!hist.length) {
    el.innerHTML = '<div class="text-muted" style="font-size:12px">暂无历史记录</div>';
    return;
  }

  el.innerHTML = hist.map((h, i) => {
    const shortId   = (h.run_id || '').slice(-12);
    const timeStr   = h.time ? h.time.replace('T', ' ').slice(0, 16) : '—';
    const srcLabel  = { wencai: '问财', all_a: '全A', manual: '手动' }[h.source_type] || h.source_type;
    const queryTip  = h.query ? h.query.slice(0, 44) + (h.query.length > 44 ? '…' : '') : srcLabel;
    const hitColor  = h.hit_count > 0 ? 'var(--green)' : 'var(--muted)';
    return `<div class="history-entry">
      <div class="history-entry-header">
        <span class="history-run-id" title="${esc(h.run_id)}">${esc(shortId)}</span>
        <span class="history-hit-badge" style="color:${hitColor}">▶ ${h.hit_count} 命中</span>
      </div>
      <div class="history-entry-meta" title="${esc(h.query)}">${esc(queryTip)}</div>
      <div style="font-size:10px;color:var(--muted);margin-bottom:4px">${esc(timeStr)} · 来源 ${esc(srcLabel)} · 池 ${esc(String(h.scope_count))}</div>
      <div class="history-entry-actions">
        <button class="btn btn-sm" type="button" onclick="historyLoadPrompt(${i})">↗ 载入提示词</button>
        <a class="btn btn-sm" href="/api/result" target="_blank" style="text-decoration:none">📄 JSON</a>
      </div>
    </div>`;
  }).join('');

  // 清除按钮
  const clrBtn = document.getElementById('btn-clear-history');
  if (clrBtn) {
    clrBtn.onclick = () => {
      try { localStorage.removeItem(LS_RUN_HISTORY); } catch (_) {}
      renderHistory();
    };
  }
}

window.historyLoadPrompt = function(idx) {
  try {
    const hist = JSON.parse(localStorage.getItem(LS_RUN_HISTORY) || '[]');
    const h    = hist[idx];
    if (!h) return;
    _promptFillData = {
      stocks:   (h.final_codes || []).join(', ') || '（无命中）',
      strategy: h.query || h.source_type || '—',
      path:     '—',
    };
    renderPromptText();
    // 切到提示词库标签
    document.querySelectorAll('.rtab').forEach(t => {
      t.classList.toggle('rtab-active', t.dataset.rtab === 'prompts');
    });
    document.querySelectorAll('.rtab-panel').forEach(p => {
      p.classList.toggle('rtab-panel-hidden', p.id !== 'rtab-prompts');
    });
    const statusEl = document.getElementById('prompt-fill-status');
    if (statusEl) {
      statusEl.textContent = `已载入历史：${(h.final_codes || []).length} 只命中`;
      statusEl.style.color = 'var(--yellow)';
    }
  } catch (_) {}
};

// ══════════════════════════════════════════════════════════════════
// G6 管理中心
// ══════════════════════════════════════════════════════════════════

function initMgmtCenter() {
  const overlay  = $('mgmt-overlay');
  const btnOpen  = $('btn-mgmt-open');
  const btnClose = $('btn-mgmt-close');

  if (btnOpen) btnOpen.addEventListener('click', () => {
    overlay.classList.remove('hidden');
    loadMgmtHistory();
  });
  if (btnClose) btnClose.addEventListener('click', () => overlay.classList.add('hidden'));
  if (overlay) overlay.addEventListener('click', ev => {
    if (ev.target === overlay) overlay.classList.add('hidden');
  });
  document.addEventListener('keydown', ev => {
    if (ev.key === 'Escape' && overlay && !overlay.classList.contains('hidden'))
      overlay.classList.add('hidden');
  });

  // mgmt tab switching
  document.querySelectorAll('.mgmt-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.mgmt-tab').forEach(t => t.classList.remove('mgmt-tab-active'));
      document.querySelectorAll('.mgmt-panel').forEach(p => p.classList.add('mgmt-panel-hidden'));
      tab.classList.add('mgmt-tab-active');
      const panel = $('mtab-' + tab.dataset.mtab);
      if (panel) panel.classList.remove('mgmt-panel-hidden');
    });
  });

  // reload history
  const btnReload = $('btn-reload-history');
  if (btnReload) btnReload.addEventListener('click', loadMgmtHistory);

  // three-layer cache clear
  ['source', 'kline', 'skill'].forEach(layer => {
    const btn = $('btn-clear-' + layer);
    if (btn) btn.addEventListener('click', () => clearCacheLayer(layer));
  });

  // wencai auth check
  const btnW = $('btn-check-wencai');
  if (btnW) btnW.addEventListener('click', checkWencaiAuth);

  // settings save
  const btnSettings = $('btn-save-settings');
  if (btnSettings) btnSettings.addEventListener('click', saveMgmtSettings);
}

// ── 管理中心：从服务端加载历史 ───────────────────────────────────────
async function loadMgmtHistory() {
  const listEl = $('mgmt-history-list');
  if (!listEl) return;
  listEl.innerHTML = '<div class="text-muted" style="font-size:12px">加载中…</div>';
  try {
    const res  = await fetch(API.runs);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    const runs = data.runs || [];
    if (!runs.length) {
      listEl.innerHTML = '<div class="text-muted" style="font-size:12px">暂无历史运行记录</div>';
      return;
    }
    listEl.innerHTML = runs.map(r => {
      const runId   = r.run_id || '';
      const shortId = runId.slice(-12);
      const timeStr = (r.generated_at || r.time || '').replace('T', ' ').slice(0, 16);
      const hits    = r.hit_count ?? r.final_hit_count ?? '?';
      const src     = r.source_type || '?';
      const hitColor = parseInt(hits, 10) > 0 ? 'var(--green)' : 'var(--muted)';
      const queryTip = (r.query || src).slice(0, 44);
      return `<div class="history-entry">
        <div class="history-entry-header">
          <span class="history-run-id" title="${esc(runId)}">${esc(shortId)}</span>
          <span class="history-hit-badge" style="color:${hitColor}">${esc(String(hits))} 命中</span>
        </div>
        <div class="history-entry-meta" title="${esc(r.query || '')}">
          ${esc(timeStr)} · ${esc(src)} · ${esc(queryTip)}
        </div>
        <div class="history-entry-actions">
          <button class="btn btn-sm" type="button"
            onclick="restoreRunParams(${JSON.stringify(runId)})">↩ 恢复参数</button>
        </div>
      </div>`;
    }).join('');
  } catch (e) {
    listEl.innerHTML = `<div class="alert alert-warn"><span class="alert-icon">⚠️</span>`
      + `<span>加载失败: ${esc(e.message)}</span></div>`;
  }
}

window.restoreRunParams = async function(runId) {
  try {
    const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/params`);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    const restored = data.params || data.strategy_snapshot || data.strategy || {};
    _applyRestoredParams(restored);
    const overlay = $('mgmt-overlay');
    if (overlay) overlay.classList.add('hidden');
    showAlert('center-alerts', 'ok', `已恢复参数（run_id: ...${runId.slice(-8)}），未自动启动运行`);
  } catch (e) {
    showAlert('center-alerts', 'warn', `恢复参数失败: ${e.message}`);
  }
};

function _applyRestoredParams(params) {
  const src = params.source || {};
  if (src.type) {
    const r = document.querySelector(`input[name="source-type"][value="${src.type}"]`);
    if (r) { r.checked = true; r.dispatchEvent(new Event('change')); }
  }
  if (params.path_type) {
    const r = document.querySelector(`input[name="path-type"][value="${params.path_type}"]`);
    if (r) r.checked = true;
  }
  const skillsArr = params.skills || params.selected_skills || [];
  document.querySelectorAll('#skill-list input[type=checkbox][data-live="true"]').forEach(cb => {
    const checked = skillsArr.includes(cb.value);
    if (cb.checked !== checked) { cb.checked = checked; cb.dispatchEvent(new Event('change')); }
  });
  const sp = (params.params || {}).skills || {};
  for (const [id, vals] of Object.entries(sp)) {
    for (const [name, val] of Object.entries(vals)) {
      const el = document.getElementById(`p-${id}-${name}`);
      if (el) el.value = String(val);
    }
  }
  if (src.query)  { const el = $('wencai-query'); if (el) el.value = src.query; }
  { const el = $('wencai-limit'); if (el) el.value = '0';
    const al = $('all-a-limit');   if (al) al.value = '0'; }
  { const rs = $('run-scope-limit'); if (rs) rs.value = String(params.run_scope_limit ?? 500); }
  if (Array.isArray(src.codes)) {
    const el = $('manual-codes');
    if (el) el.value = src.codes.join(', ');
  }
  const bridge = params.bridge || {};
  const be = $('bridge-enabled');
  if (be) be.checked = !!(bridge.mode && bridge.wencai_query);
  if (bridge.mode) {
    const bm = $('bridge-mode');
    if (bm) bm.value = bridge.mode;
  }
  if (bridge.wencai_query) {
    const bq = $('bridge-query');
    if (bq) bq.value = bridge.wencai_query;
  }
  { const bl = $('bridge-limit'); if (bl) bl.value = '0'; }
  updateBridgeConfig();
  saveParams();
}

// ── 管理中心：三层缓存清理 ────────────────────────────────────────────
async function clearCacheLayer(layer) {
  const resultEl = $('clear-' + layer + '-result');
  const btn      = $('btn-clear-' + layer);
  if (resultEl) { resultEl.style.color = 'var(--muted)'; resultEl.textContent = '清理中…'; }
  if (btn) btn.disabled = true;
  try {
    const res  = await fetch(`/api/cache/clear/${layer}`, { method: 'POST' });
    const data = await res.json();
    if (resultEl) {
      resultEl.style.color = res.ok ? 'var(--green)' : 'var(--red)';
      resultEl.textContent = res.ok
        ? (data.message || '已清理') + (data.deleted != null ? ` (${data.deleted} 个文件)` : '')
        : (data.error || '清理失败');
    }
  } catch (e) {
    if (resultEl) { resultEl.style.color = 'var(--red)'; resultEl.textContent = e.message; }
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── 管理中心：问财授权检查 ────────────────────────────────────────────
async function checkWencaiAuth() {
  const el  = $('wencai-auth-status');
  const btn = $('btn-check-wencai');
  if (el) el.innerHTML = '<span class="text-muted">检查中…</span>';
  if (btn) btn.disabled = true;
  try {
    const res  = await fetch(API.wencaiStatus);
    const data = await res.json();
    if (!el) return;
    const rows = [
      ['pywencai 已安装',       data.pywencai_installed ? '✅ 是' : '❌ 否',
        data.pywencai_installed ? 'text-green' : 'text-red'],
      ['IWENCAI_API_KEY 已配置', data.env_key_present ? '✅ 是' : '⚠ 未配置',
        data.env_key_present ? 'text-green' : 'text-yellow'],
      ['当前状态', data.status || '—',
        data.status === 'ready' ? 'text-green' : 'text-yellow'],
    ];
    const rowsHtml = rows.map(([l, v, c]) =>
      `<div class="cov-item"><span class="cov-label">${esc(l)}</span>`
      + `<span class="cov-value ${c}">${esc(v)}</span></div>`
    ).join('');
    const note = data.auth_mechanism || '';
    el.innerHTML = `<div class="coverage-grid">${rowsHtml}</div>`
      + (note ? `<div class="form-hint mt4">${esc(note)}</div>` : '');
  } catch (e) {
    if (el) el.innerHTML = `<span class="text-red">检查失败: ${esc(e.message)}</span>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── 管理中心：设置 ────────────────────────────────────────────────────
function saveMgmtSettings() {
  const pathEl = $('setting-default-path');
  const tip    = $('settings-save-tip');
  if (pathEl) {
    const r = document.querySelector(`input[name="path-type"][value="${pathEl.value}"]`);
    if (r) r.checked = true;
  }
  if (tip) {
    tip.style.display = '';
    setTimeout(() => { tip.style.display = 'none'; }, 1500);
  }
}

// ══════════════════════════════════════════════════════════════════
// G2 全局解释层渲染
// ══════════════════════════════════════════════════════════════════

function renderGlobalExplanation(r) {
  const section = $('global-explanation-section');
  const body    = $('global-explanation-body');
  const badge   = $('why-zero-badge');
  const expl    = r.global_explanation;

  if (!expl || !section || !body) return;
  section.classList.remove('hidden');

  const hitCount = expl.final_hit_count ?? (r.final_hit_codes || []).length;
  if (badge) badge.classList.toggle('hidden', hitCount > 0);

  function _explRow(label, value, cls) {
    return `<div class="cov-item"><span class="cov-label">${esc(label)}</span>`
      + `<span class="cov-value ${cls || ''}">${esc(String(value ?? '—'))}</span></div>`;
  }
  function _explLayer(name, ok, rowsHtml, suggestion) {
    const ind = ok ? '✅' : '⚠';
    const indCls = ok ? 'text-green' : 'text-yellow';
    return `<div class="expl-layer">`
      + `<div class="expl-layer-name"><span class="${indCls}">${ind}</span> ${esc(name)}</div>`
      + `<div class="expl-layer-text"><div class="coverage-grid">${rowsHtml}</div>`
      + (suggestion ? `<div class="form-hint mt4 text-yellow">${esc(suggestion)}</div>` : '')
      + `</div></div>`;
  }

  const src = expl.source_layer || {};
  const dat = expl.data_layer   || {};
  const skl = expl.skill_layer  || {};
  const pth = expl.path_layer   || {};
  const rpt = expl.report_layer || {};

  const sourceHtml = _explLayer('来源层', src.ok, [
    _explRow('来源类型', src.source_type, ''),
    _explRow('股票数量', src.actual_count, src.actual_count > 0 ? 'text-green' : 'text-red'),
    _explRow('数量说明', src.count_note || '—', ''),
  ].join(''), src.suggestion);

  const dataHtml = _explLayer('数据层', dat.ok, [
    _explRow('就绪状态', dat.readiness, dat.readiness === 'ready' ? 'text-green' : 'text-yellow'),
    _explRow('命中缓存', dat.cached, ''),
    _explRow('失败',     dat.failed, dat.failed > 0 ? 'text-red' : ''),
    _explRow('降级',     dat.stale,  dat.stale  > 0 ? 'text-yellow' : ''),
  ].join(''), dat.suggestion);

  const skillRowsHtml = (skl.skills || []).map(s =>
    `<div class="cov-item"><span class="cov-label">${esc(s.skill_id || '?')}</span>`
    + `<span class="cov-value ${s.hit_count > 0 ? 'text-green' : 'text-red'}">`
    + `输入 ${s.input_count ?? '?'} | 命中 ${s.hit_count ?? 0} | 未中 ${s.miss_count ?? 0}`
    + `</span></div>`
  ).join('');
  const skillHtml = _explLayer('技能层', skl.ok, skillRowsHtml, skl.suggestion);

  const pathHtml = _explLayer('路径层', pth.ok, [
    _explRow('路径类型',   pth.path_type,        ''),
    _explRow('步骤数',     pth.step_count,        ''),
    _explRow('清零步骤',   pth.first_zero_step || '—', pth.first_zero_step ? 'text-red' : ''),
  ].join(''), pth.suggestion);

  const rptHtml = _explLayer('报告层', rpt.ok, [
    _explRow('最终命中', rpt.final_hit_count, rpt.final_hit_count > 0 ? 'text-green' : 'text-red'),
  ].join(''), rpt.suggestion);

  const whyZeroHtml = expl.why_zero
    ? `<div class="expl-layer" style="border-left-color:var(--yellow)">`
      + `<div class="expl-layer-name" style="color:var(--yellow)">⚠ 零命中归因</div>`
      + `<div class="expl-layer-text" style="color:var(--yellow)">${esc(expl.why_zero)}</div>`
      + `</div>`
    : '';

  body.innerHTML = sourceHtml + dataHtml + skillHtml + pathHtml + rptHtml + whyZeroHtml
    || '<span class="text-muted">无解释数据</span>';
}

// ══════════════════════════════════════════════════════════════════
// G5 数据血缘渲染
// ══════════════════════════════════════════════════════════════════

function renderDataProvenance(r) {
  const section = $('data-provenance-section');
  const body    = $('data-provenance-body');
  const prov    = r.data_provenance;

  if (!prov || !section || !body) return;
  section.classList.remove('hidden');

  const modeLabel = prov.fetch_mode === 'prefetch' ? '🌐 新拉行情' : '💾 仅读缓存';
  const stats = [
    [modeLabel,          null,                    ''],
    ['总股票数',         prov.total   ?? '—',     ''],
    ['新拉行情',         prov.fetched_new ?? 0,   'text-green'],
    ['命中缓存',         prov.from_cache  ?? 0,   'text-green'],
    ['降级旧数据',       prov.degraded    ?? 0,   prov.degraded > 0 ? 'text-yellow' : ''],
    ['失败',             prov.failed      ?? 0,   prov.failed   > 0 ? 'text-red' : ''],
    ['最旧数据日',       prov.oldest_data_date || '—', ''],
  ];

  const statsHtml = `<div class="prov-stat-row">`
    + stats.map(([label, val, cls]) => {
        const display = val === null ? label : `<b class="${cls}">${esc(String(val))}</b> ${esc(label)}`;
        return `<span class="prov-stat">${display}</span>`;
      }).join('')
    + `</div>`;

  const perStock = prov.per_stock || {};
  const entries = Object.entries(perStock);
  const rows = entries.slice(0, 25).map(([code, meta]) => {
    const source = meta.source || '—';
    const fresh = meta.is_new_fetch ? '新拉' : '本地';
    const degrade = meta.is_degraded ? '降级' : '正常';
    const latest = meta.latest_date || '—';
    const trust = meta.trust_level || '—';
    return `<div class="prov-stock-row">`
      + `<span class="prov-stock-code">${esc(code)}</span>`
      + `<span>${esc(source)}</span>`
      + `<span class="${meta.is_new_fetch ? 'text-green' : ''}">${fresh}</span>`
      + `<span class="${meta.is_degraded ? 'text-yellow' : ''}">${degrade}</span>`
      + `<span>${esc(latest)} / ${esc(trust)}</span>`
      + `</div>`;
  }).join('');
  const stockHtml = entries.length
    ? `<div class="prov-stock-table">`
      + `<div class="prov-stock-row"><span>股票</span><span>来源</span><span>取数</span><span>状态</span><span>日期 / 可信度</span></div>`
      + rows
      + `</div>`
      + (entries.length > 25 ? `<div class="form-hint mt4">仅展示前 25 只，完整逐股血缘见 run_report.json。</div>` : '')
    : `<div class="form-hint mt4">本轮未产生逐股血缘。</div>`;

  body.innerHTML = statsHtml + stockHtml;
}

function renderBridgeResult(r) {
  const section = $('bridge-result-section');
  const body    = $('bridge-result-body');
  const br      = r.bridge_result || {};
  if (!section || !body || !br.mode) return;
  section.classList.remove('hidden');

  const rows = [
    ['模式', br.mode || '—', ''],
    ['是否执行', br.applied ? '是' : '否', br.applied ? 'text-green' : 'text-yellow'],
    ['问财返回', br.wencai_returned ?? '—', ''],
    ['执行前股票池', br.pool_before ?? '—', ''],
    ['执行后股票池', br.pool_after ?? '—', ''],
    ['标注命中', br.annotated_count ?? '—', ''],
  ].map(([label, val, cls]) =>
    `<div class="cov-item"><span class="cov-label">${esc(label)}</span>`
    + `<span class="cov-value ${cls}">${esc(String(val))}</span></div>`
  ).join('');

  body.innerHTML = `<div class="coverage-grid">${rows}</div>`
    + (br.wencai_query ? `<div class="form-hint mt4">问财语句：${esc(br.wencai_query)}</div>` : '')
    + (br.description ? `<div class="form-hint mt4">${esc(br.description)}</div>` : '');
}
