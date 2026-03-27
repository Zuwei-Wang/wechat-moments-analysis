const ANALYSIS_PAYLOAD_KEY = "moments_analysis_payload";

const AUDIENCE_TYPE_PROFILE = {
  family: { label: "家人", benefit: 0.52, risk: 0.24 },
  close_friend: { label: "亲密朋友", benefit: 0.78, risk: 0.3 },
  classmate_colleague: { label: "同学/同事", benefit: 0.58, risk: 0.48 },
  acquaintance: { label: "不熟联系人", benefit: 0.32, risk: 0.68 },
  special: { label: "特殊对象", benefit: 0.45, risk: 0.72 },
};

const DETAIL_PAGE_SIZE = 5;
let detailRowsState = [];
let detailCurrentPage = 1;

function buildAudienceTypeOptions(selectedType) {
  return Object.entries(AUDIENCE_TYPE_PROFILE)
    .map(([key, item]) => `<option value="${key}" ${key === selectedType ? "selected" : ""}>${item.label}</option>`)
    .join("");
}

function createAudienceRow(audienceBody, defaults = {}) {
  const audienceType = defaults.audienceType || "classmate_colleague";
  const ratioPercent = Math.round((defaults.ratio ?? 0.2) * 100);
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input name="name" placeholder="如：家人" value="${defaults.name || ""}" /></td>
    <td>
      <div class="ratio-cell">
        <input name="ratio" type="range" min="0" max="100" step="1" value="${ratioPercent}" />
        <span class="ratio-value">${ratioPercent}%</span>
      </div>
    </td>
    <td>
      <select name="audienceType">
        ${buildAudienceTypeOptions(audienceType)}
      </select>
    </td>
    <td>
      <select name="complexity">
        <option value="low" ${defaults.complexity === "low" ? "selected" : ""}>低</option>
        <option value="medium" ${defaults.complexity === "medium" || !defaults.complexity ? "selected" : ""}>中</option>
        <option value="high" ${defaults.complexity === "high" ? "selected" : ""}>高</option>
      </select>
    </td>
    <td><input name="inGroup" type="checkbox" ${defaults.inGroup !== false ? "checked" : ""} /></td>
    <td><button class="danger" type="button">删除</button></td>
  `;

  tr.querySelector("button").addEventListener("click", () => {
    tr.remove();
  });

  tr.querySelector("[name='ratio']").addEventListener("input", (event) => {
    tr.querySelector(".ratio-value").textContent = `${event.target.value}%`;
  });

  audienceBody.appendChild(tr);
}

function collectPayload() {
  const contentTypeEl = document.getElementById("contentType");
  const postingTimeEl = document.getElementById("postingTime");
  const blockedAudienceInput = document.getElementById("blockedAudienceInput");
  const audienceBody = document.getElementById("audienceBody");

  if (!contentTypeEl || !postingTimeEl || !blockedAudienceInput || !audienceBody) {
    return null;
  }

  const contentType = contentTypeEl.value;
  const postingTime = postingTimeEl.value;
  const sensitiveTags = Array.from(
    document.querySelectorAll("fieldset input[type='checkbox']:checked")
  ).map((input) => input.value);
  const blockedAudienceNames = blockedAudienceInput.value
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean);

  const audiences = Array.from(audienceBody.querySelectorAll("tr")).map((row) => {
    const read = (name) => row.querySelector(`[name='${name}']`).value;
    const inGroup = row.querySelector("[name='inGroup']").checked;
    return {
      name: read("name"),
      ratio: Number(read("ratio")) / 100,
      audienceType: read("audienceType"),
      complexity: read("complexity"),
      inGroup,
    };
  });

  return { contentType, postingTime, sensitiveTags, blockedAudienceNames, audiences };
}

function renderDetailPage() {
  const detailBody = document.getElementById("detailBody");
  const detailPrevBtn = document.getElementById("detailPrevBtn");
  const detailNextBtn = document.getElementById("detailNextBtn");
  const detailPageInfo = document.getElementById("detailPageInfo");

  if (!detailBody || !detailPrevBtn || !detailNextBtn || !detailPageInfo) {
    return;
  }

  detailBody.innerHTML = "";
  if (!detailRowsState.length) {
    detailPageInfo.textContent = "第 0 / 0 页";
    detailPrevBtn.disabled = true;
    detailNextBtn.disabled = true;
    return;
  }

  const totalPages = Math.ceil(detailRowsState.length / DETAIL_PAGE_SIZE);
  if (detailCurrentPage > totalPages) {
    detailCurrentPage = totalPages;
  }

  const start = (detailCurrentPage - 1) * DETAIL_PAGE_SIZE;
  const end = start + DETAIL_PAGE_SIZE;
  const rows = detailRowsState.slice(start, end);

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

  detailPageInfo.textContent = `第 ${detailCurrentPage} / ${totalPages} 页`;
  detailPrevBtn.disabled = detailCurrentPage <= 1;
  detailNextBtn.disabled = detailCurrentPage >= totalPages;
}

function renderResult(result) {
  const resultCard = document.getElementById("resultCard");
  const summary = document.getElementById("summary");
  const riskDimensionCards = document.getElementById("riskDimensionCards");
  const actionSuggestionList = document.getElementById("actionSuggestionList");
  const topRiskList = document.getElementById("topRiskList");
  const visibilityBody = document.getElementById("visibilityBody");
  const bestScenarioText = document.getElementById("bestScenarioText");

  if (
    !resultCard
    || !summary
    || !riskDimensionCards
    || !actionSuggestionList
    || !topRiskList
    || !visibilityBody
    || !bestScenarioText
  ) {
    return;
  }

  resultCard.hidden = false;
  const percentScore = Math.min(100, Math.max(0, Number(result.utilityScore)));

  summary.className = `summary ${result.level}`;
  summary.innerHTML = `
    <div class="score-hero">
      <div class="score-ring" style="--score:${percentScore};">
        <div class="score-ring-inner">
          <div class="score-value">${percentScore}</div>
          <div class="score-unit">/100</div>
        </div>
      </div>
      <div class="score-meta">
        <p class="score-title">综合得分</p>
        <p><span class="suggestion-badge ${result.level}">${result.suggestion}</span></p>
        <p><strong>原始效用值 U:</strong> ${result.utilityRaw}</p>
        <p><strong>敏感度加权:</strong> ${result.meta.sensitivityRisk}</p>
        <p><strong>发布时间影响:</strong> 收益 x${result.meta.timeBenefitFactor}，风险 x${result.meta.timeRiskFactor}</p>
      </div>
    </div>
  `;

  riskDimensionCards.innerHTML = "";
  (result.riskDimensions || []).forEach((item) => {
    const percent = Math.round((item.share || 0) * 100);
    const card = document.createElement("article");
    card.className = "risk-dimension-card";
    card.innerHTML = `
      <p class="risk-dimension-label">${item.label}</p>
      <p class="risk-dimension-percent">${percent}%</p>
      <p class="risk-dimension-value">风险贡献 ${item.value}</p>
      <div class="risk-dimension-track">
        <span style="width:${percent}%"></span>
      </div>
    `;
    riskDimensionCards.appendChild(card);
  });

  actionSuggestionList.innerHTML = "";
  (result.actionSuggestions || []).forEach((item) => {
    const delta = Number(item.estimatedDeltaScore || 0);
    const card = document.createElement("article");
    card.className = "suggestion-card";
    card.innerHTML = `
      <p class="suggestion-title">
        ${item.title}
        <span class="delta-chip">+${delta.toFixed(1)} 分</span>
      </p>
      <p class="suggestion-detail">${item.detail}</p>
    `;
    actionSuggestionList.appendChild(card);
  });

  topRiskList.innerHTML = "";
  result.topRiskContributors.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.name}: 风险贡献 ${item.risk}`;
    topRiskList.appendChild(li);
  });

  detailRowsState = result.details.slice();
  detailCurrentPage = 1;
  renderDetailPage();

  visibilityBody.innerHTML = "";
  result.visibilitySimulation.scenarios.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = item.available
      ? `
        <td>${item.label}</td>
        <td>${item.utilityScore} / 100</td>
        <td>${item.suggestion}</td>
      `
      : `
        <td>${item.label}</td>
        <td>-</td>
        <td>${item.reason}</td>
      `;
    visibilityBody.appendChild(tr);
  });

  if (result.visibilitySimulation.bestScenario) {
    const best = result.visibilitySimulation.bestScenario;
    bestScenarioText.textContent = `当前输入下最优方案：${best.label}（评分 ${best.utilityScore} / 100，${best.suggestion}）`;
  } else {
    bestScenarioText.textContent = "当前无法给出可见方案建议。";
  }
}

async function fetchAndRenderResult(payload) {
  const errorBox = document.getElementById("errorBox");
  if (errorBox) {
    errorBox.hidden = true;
  }

  try {
    const response = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "评估失败");
    }

    renderResult(data);
  } catch (error) {
    if (errorBox) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    }
  }
}

function initStartPage() {
  const audienceBody = document.getElementById("audienceBody");
  const addAudienceBtn = document.getElementById("addAudience");
  const startAnalysisBtn = document.getElementById("startAnalysisBtn");
  const errorBox = document.getElementById("errorBox");

  if (!audienceBody || !addAudienceBtn || !startAnalysisBtn) {
    return;
  }

  const cached = sessionStorage.getItem(ANALYSIS_PAYLOAD_KEY);
  if (cached) {
    try {
      const payload = JSON.parse(cached);
      document.getElementById("contentType").value = payload.contentType || "daily";
      document.getElementById("postingTime").value = payload.postingTime || "daytime";
      document.getElementById("blockedAudienceInput").value = (payload.blockedAudienceNames || []).join(", ");

      (payload.sensitiveTags || []).forEach((tag) => {
        const checkbox = document.querySelector(`fieldset input[value='${tag}']`);
        if (checkbox) {
          checkbox.checked = true;
        }
      });

      if (Array.isArray(payload.audiences) && payload.audiences.length) {
        payload.audiences.forEach((row) => createAudienceRow(audienceBody, row));
      }
    } catch {
      // ignore invalid cache and fallback to defaults
    }
  }

  if (!audienceBody.children.length) {
    createAudienceRow(audienceBody, { name: "家人", ratio: 0.2, audienceType: "family", complexity: "low", inGroup: true });
    createAudienceRow(audienceBody, { name: "亲密朋友", ratio: 0.3, audienceType: "close_friend", complexity: "low", inGroup: true });
    createAudienceRow(audienceBody, { name: "同学/同事", ratio: 0.3, audienceType: "classmate_colleague", complexity: "medium", inGroup: true });
    createAudienceRow(audienceBody, { name: "不熟联系人", ratio: 0.2, audienceType: "acquaintance", complexity: "high", inGroup: false });
  }

  addAudienceBtn.addEventListener("click", () => createAudienceRow(audienceBody));
  startAnalysisBtn.addEventListener("click", () => {
    if (errorBox) {
      errorBox.hidden = true;
    }

    const payload = collectPayload();
    if (!payload) {
      return;
    }

    try {
      sessionStorage.setItem(ANALYSIS_PAYLOAD_KEY, JSON.stringify(payload));
      window.location.href = "/analysis-result";
    } catch {
      if (errorBox) {
        errorBox.textContent = "保存分析参数失败，请重试。";
        errorBox.hidden = false;
      }
    }
  });
}

function initResultPage() {
  const resultCard = document.getElementById("resultCard");
  if (!resultCard) {
    return;
  }

  const detailPrevBtn = document.getElementById("detailPrevBtn");
  const detailNextBtn = document.getElementById("detailNextBtn");
  const errorBox = document.getElementById("errorBox");

  if (detailPrevBtn) {
    detailPrevBtn.addEventListener("click", () => {
      if (detailCurrentPage > 1) {
        detailCurrentPage -= 1;
        renderDetailPage();
      }
    });
  }

  if (detailNextBtn) {
    detailNextBtn.addEventListener("click", () => {
      const totalPages = Math.ceil(detailRowsState.length / DETAIL_PAGE_SIZE);
      if (detailCurrentPage < totalPages) {
        detailCurrentPage += 1;
        renderDetailPage();
      }
    });
  }

  const payloadText = sessionStorage.getItem(ANALYSIS_PAYLOAD_KEY);
  if (!payloadText) {
    if (errorBox) {
      errorBox.textContent = "没有找到分析参数，请先到“开始分析”页面填写。";
      errorBox.hidden = false;
    }
    return;
  }

  try {
    const payload = JSON.parse(payloadText);
    fetchAndRenderResult(payload);
  } catch {
    if (errorBox) {
      errorBox.textContent = "读取分析参数失败，请返回重新填写。";
      errorBox.hidden = false;
    }
  }
}

initStartPage();
initResultPage();
