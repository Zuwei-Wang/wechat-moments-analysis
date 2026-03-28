import { AUDIENCE_TYPE_PROFILE, DETAIL_PAGE_SIZE, state } from "./constants.js";
import { deepClone, loadPayload, normalizePayload, savePayload, readCompareSlots, writeCompareSlots } from "./storage.js";

function formatSlotSummary(slot) {
  if (!slot) return "未保存";
  return `${slot.result.utilityScore} 分 / ${slot.result.suggestion} / ${slot.result.meta.selectedVisibilityPlanLabel}`;
}

function renderComparePanel() {
  const slotAInfo = document.getElementById("slotAInfo");
  const slotBInfo = document.getElementById("slotBInfo");
  const compareBody = document.getElementById("compareBody");
  if (!slotAInfo || !slotBInfo || !compareBody) return;

  const slots = readCompareSlots();
  slotAInfo.textContent = `方案 A：${formatSlotSummary(slots.A)}`;
  slotBInfo.textContent = `方案 B：${formatSlotSummary(slots.B)}`;

  compareBody.innerHTML = "";
  if (!slots.A || !slots.B) {
    const tr = document.createElement("tr");
    tr.innerHTML = "<td>提示</td><td colspan=\"3\">请先分别保存方案 A 和方案 B，再查看差异。</td>";
    compareBody.appendChild(tr);
    return;
  }

  const a = slots.A.result;
  const b = slots.B.result;
  const rows = [
    { name: "综合得分", a: `${a.utilityScore}`, b: `${b.utilityScore}`, delta: (b.utilityScore - a.utilityScore).toFixed(1) },
    { name: "原始效用 U", a: `${a.utilityRaw}`, b: `${b.utilityRaw}`, delta: (b.utilityRaw - a.utilityRaw).toFixed(3) },
    { name: "建议", a: a.suggestion, b: b.suggestion, delta: "-" },
    {
      name: "主风险维度",
      a: `${a.riskDimensions?.[0]?.label || "-"} ${Math.round((a.riskDimensions?.[0]?.share || 0) * 100)}%`,
      b: `${b.riskDimensions?.[0]?.label || "-"} ${Math.round((b.riskDimensions?.[0]?.share || 0) * 100)}%`,
      delta: "-",
    },
    { name: "可见方案", a: a.meta?.selectedVisibilityPlanLabel || "-", b: b.meta?.selectedVisibilityPlanLabel || "-", delta: "-" },
  ];

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.name}</td><td>${row.a}</td><td>${row.b}</td><td>${row.delta}</td>`;
    compareBody.appendChild(tr);
  });
}

function saveCurrentToSlot(slotName) {
  if (!state.currentPayload || !state.currentResult) return;
  const slots = readCompareSlots();
  slots[slotName] = {
    payload: deepClone(state.currentPayload),
    result: deepClone(state.currentResult),
    savedAt: new Date().toISOString(),
  };
  writeCompareSlots(slots);
  renderComparePanel();
}

function applySlot(slotName, fetchAndRenderResult) {
  const slots = readCompareSlots();
  const slot = slots[slotName];
  if (!slot) return;
  const payload = normalizePayload(slot.payload);
  state.currentPayload = payload;
  savePayload(payload);
  fetchAndRenderResult(payload);
}

function applySuggestionAction(payload, action) {
  if (!action || !action.type) return payload;
  const next = normalizePayload(payload);
  if (action.type === "remove_sensitive_tags") {
    const removeSet = new Set(action.tags || []);
    next.sensitiveTags = next.sensitiveTags.filter((tag) => !removeSet.has(tag));
  } else if (action.type === "set_posting_time") {
    next.postingTime = action.postingTime || next.postingTime;
  } else if (action.type === "set_visibility_plan") {
    next.selectedVisibilityPlan = action.plan || next.selectedVisibilityPlan;
  }
  return next;
}

function renderDetailPage() {
  const detailBody = document.getElementById("detailBody");
  const detailPrevBtn = document.getElementById("detailPrevBtn");
  const detailNextBtn = document.getElementById("detailNextBtn");
  const detailPageInfo = document.getElementById("detailPageInfo");
  if (!detailBody || !detailPrevBtn || !detailNextBtn || !detailPageInfo) return;

  detailBody.innerHTML = "";
  if (!state.detailRowsState.length) {
    detailPageInfo.textContent = "第 0 / 0 页";
    detailPrevBtn.disabled = true;
    detailNextBtn.disabled = true;
    return;
  }

  const totalPages = Math.ceil(state.detailRowsState.length / DETAIL_PAGE_SIZE);
  if (state.detailCurrentPage > totalPages) state.detailCurrentPage = totalPages;
  const start = (state.detailCurrentPage - 1) * DETAIL_PAGE_SIZE;
  const rows = state.detailRowsState.slice(start, start + DETAIL_PAGE_SIZE);

  rows.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.name}</td>
      <td>${AUDIENCE_TYPE_PROFILE[item.audienceType]?.label || item.audienceType}</td>
      <td>${item.baseBenefit}</td>
      <td>${item.baseRisk}</td>
      <td>${item.weight}</td>
      <td>${item.gain}</td>
      <td>${item.risk}</td>
      <td>${item.utility}</td>
    `;
    detailBody.appendChild(tr);
  });

  detailPageInfo.textContent = `第 ${state.detailCurrentPage} / ${totalPages} 页`;
  detailPrevBtn.disabled = state.detailCurrentPage <= 1;
  detailNextBtn.disabled = state.detailCurrentPage >= totalPages;
}

function renderHistoryPanel(historyData) {
  const historySummary = document.getElementById("historySummary");
  const historyTrendBody = document.getElementById("historyTrendBody");
  const highRiskTagList = document.getElementById("highRiskTagList");
  if (!historySummary || !historyTrendBody || !highRiskTagList) return;

  if (!historyData || !historyData.total) {
    historySummary.innerHTML = "<p>暂无历史记录，完成几次分析后可查看趋势与高风险标签统计。</p>";
    historyTrendBody.innerHTML = "<tr><td colspan=\"3\">暂无数据</td></tr>";
    highRiskTagList.innerHTML = "<li>暂无数据</li>";
    return;
  }

  const counts = historyData.riskLevelCounts || { safe: 0, warning: 0, danger: 0 };
  historySummary.innerHTML = `
    <p>近 ${historyData.total} 次平均得分：<strong>${historyData.avgScore}</strong></p>
    <p>风险等级分布：安全 ${counts.safe} / 谨慎 ${counts.warning} / 高风险 ${counts.danger}</p>
  `;

  historyTrendBody.innerHTML = "";
  (historyData.trend || []).forEach((item) => {
    const tr = document.createElement("tr");
    const levelText = item.level === "safe" ? "安全" : item.level === "danger" ? "高风险" : "谨慎";
    tr.innerHTML = `<td>${item.x}</td><td>${item.score}</td><td>${levelText}</td>`;
    historyTrendBody.appendChild(tr);
  });

  highRiskTagList.innerHTML = "";
  const highRiskTags = historyData.highRiskTags || [];
  if (!highRiskTags.length) {
    const li = document.createElement("li");
    li.textContent = "最近记录中暂无明显高风险标签聚集。";
    highRiskTagList.appendChild(li);
    return;
  }
  highRiskTags.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.tag}: ${item.count} 次`;
    highRiskTagList.appendChild(li);
  });
}

function renderPersonalization(profile) {
  const personalizationCard = document.getElementById("personalizationCard");
  if (!personalizationCard) return;
  if (!profile) {
    personalizationCard.innerHTML = "<p>暂无个性化参数。</p>";
    return;
  }
  personalizationCard.innerHTML = `
    <p><strong>收益权重倍率：</strong>${Number(profile.benefitMultiplier || 1).toFixed(3)}</p>
    <p><strong>风险权重倍率：</strong>${Number(profile.riskMultiplier || 1).toFixed(3)}</p>
    <p><strong>最近更新时间：</strong>${profile.updatedAt || "-"}</p>
  `;
}

async function fetchHistoryDashboard(limit = 20) {
  try {
    const response = await fetch(`/api/history?limit=${limit}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "获取历史记录失败");
    renderHistoryPanel(data);
  } catch {
    renderHistoryPanel(null);
  }
}

async function clearHistoryRecords() {
  const historyActionMessage = document.getElementById("historyActionMessage");
  if (historyActionMessage) historyActionMessage.textContent = "";
  const confirmed = window.confirm("确认清空全部历史记录吗？该操作不可撤销。");
  if (!confirmed) return;
  try {
    const response = await fetch("/api/history/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "清空历史记录失败");
    if (historyActionMessage) historyActionMessage.textContent = `已清空 ${data.deleted || 0} 条历史记录。`;
    fetchHistoryDashboard(20);
  } catch (error) {
    if (historyActionMessage) historyActionMessage.textContent = error.message || "清空历史记录失败";
  }
}

function renderResult(result, fetchAndRenderResult) {
  const resultCard = document.getElementById("resultCard");
  const summary = document.getElementById("summary");
  const copyAnalysisCard = document.getElementById("copyAnalysisCard");
  const scoreExplanationList = document.getElementById("scoreExplanationList");
  const riskDimensionCards = document.getElementById("riskDimensionCards");
  const actionSuggestionList = document.getElementById("actionSuggestionList");
  const topRiskList = document.getElementById("topRiskList");
  const visibilityBody = document.getElementById("visibilityBody");
  const bestScenarioText = document.getElementById("bestScenarioText");
  if (
    !resultCard ||
    !summary ||
    !copyAnalysisCard ||
    !scoreExplanationList ||
    !riskDimensionCards ||
    !actionSuggestionList ||
    !topRiskList ||
    !visibilityBody ||
    !bestScenarioText
  ) {
    return;
  }

  state.currentResult = result;
  resultCard.hidden = false;
  const percentScore = Math.min(100, Math.max(0, Number(result.utilityScore)));

  summary.className = `summary ${result.level}`;
  summary.innerHTML = `
    <div class="score-hero">
      <div class="score-ring" style="--score:${percentScore};"><div class="score-ring-inner"><div class="score-value">${percentScore}</div><div class="score-unit">/100</div></div></div>
      <div class="score-meta">
        <p class="score-title">综合得分</p>
        <p><span class="suggestion-badge ${result.level}">${result.suggestion}</span></p>
        <p><strong>原始效用值 U:</strong> ${result.utilityRaw}</p>
        <p><strong>当前可见方案:</strong> ${result.meta.selectedVisibilityPlanLabel}</p>
        <p><strong>敏感度加权:</strong> ${result.meta.sensitivityRisk}</p>
        <p><strong>发布时间影响:</strong> 收益 x${result.meta.timeBenefitFactor}，风险 x${result.meta.timeRiskFactor}</p>
      </div>
    </div>
  `;

  const copyAnalysis = result.meta.copyAnalysis;
  renderPersonalization(result.meta.personalization || null);
  const manualTags = result.meta.manualSensitiveTags || [];
  const autoTags = result.meta.autoSensitiveTags || [];
  const mergedTags = result.meta.sensitiveTags || [];
  if (!copyAnalysis) {
    copyAnalysisCard.innerHTML = `
      <p class="copy-analysis-title">未输入文案</p>
      <p class="copy-analysis-hint">当前仅基于手动勾选的敏感信息评估风险。</p>
      <p class="copy-analysis-tags"><strong>当前敏感标签：</strong>${mergedTags.length ? mergedTags.join("、") : "无"}</p>
    `;
  } else {
    const levels = [
      { label: "情绪强度", value: copyAnalysis.emotionIntensity },
      { label: "炫耀程度", value: copyAnalysis.showoffIntensity },
      { label: "隐私强度", value: copyAnalysis.privacyIntensity },
    ];
    const levelHtml = levels
      .map((item) => `<li>${item.label}：${item.value.level}（${Math.round((item.value.score || 0) * 100)}%）</li>`)
      .join("");

    copyAnalysisCard.innerHTML = `
      <p class="copy-analysis-title">文案已参与风险修正（长度 ${copyAnalysis.textLength}）</p>
      <ul class="copy-analysis-levels">${levelHtml}</ul>
      <p class="copy-analysis-tags"><strong>手动标签：</strong>${manualTags.length ? manualTags.join("、") : "无"}</p>
      <p class="copy-analysis-tags"><strong>自动识别：</strong>${autoTags.length ? autoTags.join("、") : "无"}</p>
      <p class="copy-analysis-tags"><strong>最终生效：</strong>${mergedTags.length ? mergedTags.join("、") : "无"}</p>
    `;
  }

  scoreExplanationList.innerHTML = "";
  const lowering = result.scoreExplanation?.loweringFactors || [];
  if (!lowering.length) {
    const empty = document.createElement("article");
    empty.className = "explain-item";
    empty.innerHTML = "<p class=\"explain-name\">当前没有明显的拉低因子。</p>";
    scoreExplanationList.appendChild(empty);
  } else {
    lowering.forEach((item, idx) => {
      const explain = document.createElement("article");
      explain.className = "explain-item";
      explain.innerHTML = `
        <p class="explain-name">${idx + 1}. ${item.name}</p>
        <p class="explain-meta">影响方向：拉低分数 · 贡献占比：${item.share}% · 影响值：${item.impact}</p>
        <p class="explain-detail">${item.detail}</p>
        <div class="explain-track"><span style="width:${Math.min(100, Math.max(0, item.share || 0))}%"></span></div>
      `;
      scoreExplanationList.appendChild(explain);
    });
  }

  riskDimensionCards.innerHTML = "";
  (result.riskDimensions || []).forEach((item) => {
    const percent = Math.round((item.share || 0) * 100);
    const card = document.createElement("article");
    card.className = "risk-dimension-card";
    card.innerHTML = `
      <p class="risk-dimension-label">${item.label}</p>
      <p class="risk-dimension-percent">${percent}%</p>
      <p class="risk-dimension-value">风险贡献 ${item.value}</p>
      <div class="risk-dimension-track"><span style="width:${percent}%"></span></div>
    `;
    riskDimensionCards.appendChild(card);
  });

  actionSuggestionList.innerHTML = "";
  (result.actionSuggestions || []).forEach((item) => {
    const delta = Number(item.estimatedDeltaScore || 0);
    const card = document.createElement("article");
    card.className = "suggestion-card";
    card.innerHTML = `
      <p class="suggestion-title">${item.title}<span class="delta-chip">+${delta.toFixed(1)} 分</span></p>
      <p class="suggestion-detail">${item.detail}</p>
      <button type="button" class="apply-suggestion-btn">应用并重算</button>
    `;
    card.querySelector(".apply-suggestion-btn").addEventListener("click", () => {
      if (!state.currentPayload) return;
      state.currentPayload = applySuggestionAction(state.currentPayload, item.action || { type: "noop" });
      savePayload(state.currentPayload);
      fetchAndRenderResult(state.currentPayload);
    });
    actionSuggestionList.appendChild(card);
  });

  topRiskList.innerHTML = "";
  result.topRiskContributors.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.name}: 风险贡献 ${item.risk}`;
    topRiskList.appendChild(li);
  });

  state.detailRowsState = result.details.slice();
  state.detailCurrentPage = 1;
  renderDetailPage();

  visibilityBody.innerHTML = "";
  result.visibilitySimulation.scenarios.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = item.available
      ? `<td>${item.label}</td><td>${item.utilityScore} / 100</td><td>${item.suggestion}</td>`
      : `<td>${item.label}</td><td>-</td><td>${item.reason}</td>`;
    visibilityBody.appendChild(tr);
  });

  if (result.visibilitySimulation.bestScenario) {
    const best = result.visibilitySimulation.bestScenario;
    bestScenarioText.textContent = `当前输入下最优方案：${best.label}（评分 ${best.utilityScore} / 100，${best.suggestion}）`;
  } else {
    bestScenarioText.textContent = "当前无法给出可见方案建议。";
  }

  fetchHistoryDashboard(20);
  renderComparePanel();
}

async function submitFeedback(feedbackType, fetchAndRenderResult) {
  const feedbackMessage = document.getElementById("feedbackMessage");
  if (feedbackMessage) feedbackMessage.textContent = "";
  try {
    const response = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feedbackType }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "提交反馈失败");
    if (feedbackMessage) feedbackMessage.textContent = "反馈已记录，已按你的偏好更新个性化参数。";
    if (state.currentPayload) fetchAndRenderResult(state.currentPayload);
  } catch (error) {
    if (feedbackMessage) feedbackMessage.textContent = error.message || "提交反馈失败";
  }
}

async function fetchAndRenderResult(payload) {
  const errorBox = document.getElementById("errorBox");
  if (errorBox) errorBox.hidden = true;

  try {
    const response = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "评估失败");
    renderResult(data, fetchAndRenderResult);
  } catch (error) {
    if (errorBox) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    }
  }
}

export function initResultPage() {
  const resultCard = document.getElementById("resultCard");
  if (!resultCard) return;

  const detailPrevBtn = document.getElementById("detailPrevBtn");
  const detailNextBtn = document.getElementById("detailNextBtn");
  const saveSlotABtn = document.getElementById("saveSlotABtn");
  const saveSlotBBtn = document.getElementById("saveSlotBBtn");
  const applySlotABtn = document.getElementById("applySlotABtn");
  const applySlotBBtn = document.getElementById("applySlotBBtn");
  const clearCompareBtn = document.getElementById("clearCompareBtn");
  const clearHistoryBtn = document.getElementById("clearHistoryBtn");
  const feedbackConservativeBtn = document.getElementById("feedbackConservativeBtn");
  const feedbackOptimisticBtn = document.getElementById("feedbackOptimisticBtn");
  const feedbackAccurateBtn = document.getElementById("feedbackAccurateBtn");
  const errorBox = document.getElementById("errorBox");

  detailPrevBtn?.addEventListener("click", () => {
    if (state.detailCurrentPage > 1) {
      state.detailCurrentPage -= 1;
      renderDetailPage();
    }
  });
  detailNextBtn?.addEventListener("click", () => {
    const totalPages = Math.ceil(state.detailRowsState.length / DETAIL_PAGE_SIZE);
    if (state.detailCurrentPage < totalPages) {
      state.detailCurrentPage += 1;
      renderDetailPage();
    }
  });

  saveSlotABtn?.addEventListener("click", () => saveCurrentToSlot("A"));
  saveSlotBBtn?.addEventListener("click", () => saveCurrentToSlot("B"));
  applySlotABtn?.addEventListener("click", () => applySlot("A", fetchAndRenderResult));
  applySlotBBtn?.addEventListener("click", () => applySlot("B", fetchAndRenderResult));
  clearCompareBtn?.addEventListener("click", () => {
    writeCompareSlots({ A: null, B: null });
    renderComparePanel();
  });
  clearHistoryBtn?.addEventListener("click", () => clearHistoryRecords());
  feedbackConservativeBtn?.addEventListener("click", () => submitFeedback("too_conservative", fetchAndRenderResult));
  feedbackOptimisticBtn?.addEventListener("click", () => submitFeedback("too_optimistic", fetchAndRenderResult));
  feedbackAccurateBtn?.addEventListener("click", () => submitFeedback("accurate", fetchAndRenderResult));

  renderComparePanel();
  const payload = loadPayload();
  if (!payload) {
    if (errorBox) {
      errorBox.textContent = "没有找到分析参数，请先到“开始分析”页面填写。";
      errorBox.hidden = false;
    }
    return;
  }

  state.currentPayload = payload;
  savePayload(payload);
  fetchAndRenderResult(payload);
}
