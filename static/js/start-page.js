import { AUDIENCE_TYPE_PROFILE, state } from "./constants.js";
import { clearDraft, loadDraft, loadPayload, saveDraft, savePayload } from "./storage.js";

const TOTAL_STEPS = 6;

function buildAudienceTypeOptions(selectedType) {
  return Object.entries(AUDIENCE_TYPE_PROFILE)
    .map(([key, item]) => `<option value="${key}" ${key === selectedType ? "selected" : ""}>${item.label}</option>`)
    .join("");
}

function createAudienceRow(audienceBody, defaults = {}, onChanged = () => {}) {
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
      <select name="audienceType">${buildAudienceTypeOptions(audienceType)}</select>
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
    onChanged();
  });
  tr.querySelector("[name='ratio']").addEventListener("input", (event) => {
    tr.querySelector(".ratio-value").textContent = `${event.target.value}%`;
    onChanged();
  });
  tr.querySelectorAll("input, select").forEach((el) => {
    el.addEventListener("change", onChanged);
    el.addEventListener("input", onChanged);
  });

  audienceBody.appendChild(tr);
}

function collectPayload() {
  const contentTypeEl = document.getElementById("contentType");
  const postingTimeEl = document.getElementById("postingTime");
  const blockedAudienceInput = document.getElementById("blockedAudienceInput");
  const copyTextEl = document.getElementById("copyText");
  const audienceBody = document.getElementById("audienceBody");
  if (!contentTypeEl || !postingTimeEl || !blockedAudienceInput || !audienceBody || !copyTextEl) return null;

  const contentType = contentTypeEl.value;
  const postingTime = postingTimeEl.value;
  const sensitiveTags = Array.from(document.querySelectorAll("fieldset input[type='checkbox']:checked")).map((input) => input.value);
  const blockedAudienceNames = blockedAudienceInput.value
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean);
  const copyText = copyTextEl.value.trim();
  const audiences = Array.from(audienceBody.querySelectorAll("tr")).map((row) => {
    const read = (name) => row.querySelector(`[name='${name}']`)?.value || "";
    return {
      name: read("name"),
      ratio: Number(read("ratio")) / 100,
      audienceType: read("audienceType"),
      complexity: read("complexity"),
      inGroup: !!row.querySelector("[name='inGroup']")?.checked,
    };
  });

  const hasBlockedAudience = blockedAudienceNames.length > 0;
  const hasGroupSelection = audiences.some((row) => row.inGroup === false);
  const selectedVisibilityPlan = hasBlockedAudience ? "hide_selected" : hasGroupSelection ? "group_only" : "all_visible";

  return {
    contentType,
    postingTime,
    selectedVisibilityPlan,
    sensitiveTags,
    blockedAudienceNames,
    copyText,
    audiences,
  };
}

function formatSavedAt(text) {
  if (!text) return "";
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) return "";
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(
    date.getHours()
  ).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function visibilityPlanLabel(plan) {
  if (plan === "group_only") return "仅分组可见";
  if (plan === "hide_selected") return "屏蔽指定人群";
  return "全部可见";
}

function stepHint(step) {
  return {
    1: "Step 1/6：选择内容类型",
    2: "Step 2/6：选择发布时间",
    3: "Step 3/6：勾选敏感信息",
    4: "Step 4/6：填写文案（可选）",
    5: "Step 5/6：设置受众结构",
    6: "Step 6/6：确认可见范围并提交",
  }[step];
}

export function initStartPage() {
  const audienceBody = document.getElementById("audienceBody");
  const addAudienceBtn = document.getElementById("addAudience");
  const clearDraftBtn = document.getElementById("clearDraftBtn");
  const progressBarFill = document.getElementById("progressBarFill");
  const wizardStepCount = document.getElementById("wizardStepCount");
  const wizardStepTitle = document.getElementById("wizardStepTitle");
  const draftStatus = document.getElementById("draftStatus");
  const reviewSummary = document.getElementById("reviewSummary");
  const errorBox = document.getElementById("errorBox");
  const stepSections = Array.from(document.querySelectorAll("[data-step-section]"));
  const startAnalysisBtn = document.getElementById("startAnalysisBtn");
  if (!audienceBody || !addAudienceBtn || !startAnalysisBtn) return;

  let currentStep = 1;
  let hasUnsubmittedChanges = false;
  let isNavigating = false;
  let draftTimer = null;
  let lastSubmittedSnapshot = "";

  const showError = (message) => {
    if (!errorBox) return;
    errorBox.textContent = message;
    errorBox.hidden = false;
  };

  const clearError = () => {
    if (!errorBox) return;
    errorBox.hidden = true;
  };

  const getSnapshot = () => JSON.stringify(collectPayload() || {});

  const validateStep1 = () => {
    const payload = collectPayload();
    if (!payload || !payload.contentType) {
      showError("请先选择内容类型。");
      return false;
    }
    return true;
  };

  const validateStep2 = () => {
    const payload = collectPayload();
    if (!payload || !payload.postingTime) {
      showError("请先选择发布时间。");
      return false;
    }
    return true;
  };

  const validateStep3 = () => true;

  const validateStep4 = () => {
    const payload = collectPayload();
    if (!payload) return false;
    if (payload.copyText.length > 1000) {
      showError("文案长度不能超过 1000 字。");
      return false;
    }
    return true;
  };

  const validateStep5 = () => {
    const payload = collectPayload();
    if (!payload) return false;
    const validAudienceRows = payload.audiences.filter((row) => row.name.trim() && Number(row.ratio) > 0);
    const totalRatio = validAudienceRows.reduce((sum, row) => sum + Number(row.ratio), 0);
    if (!validAudienceRows.length || totalRatio <= 0) {
      showError("请至少填写一类受众名称，并设置有效占比。");
      return false;
    }
    return true;
  };

  const canReachStep = (targetStep) => {
    if (targetStep <= 1) return true;
    if (!validateStep1()) return false;
    if (targetStep <= 2) return true;
    if (!validateStep2()) return false;
    if (targetStep <= 3) return true;
    if (!validateStep3()) return false;
    if (targetStep <= 4) return true;
    if (!validateStep4()) return false;
    if (targetStep <= 5) return true;
    return validateStep5();
  };

  const refreshProgress = () => {
    if (!progressBarFill) return;
    const percent = Math.round(((currentStep - 1) / (TOTAL_STEPS - 1)) * 100);
    progressBarFill.style.width = `${percent}%`;
    progressBarFill.title = stepHint(currentStep);
    progressBarFill.setAttribute("aria-label", `当前流程进度 ${percent}%`);
    if (wizardStepCount) wizardStepCount.textContent = `步骤 ${currentStep} / ${TOTAL_STEPS}`;
    if (wizardStepTitle) wizardStepTitle.textContent = stepHint(currentStep)?.replace(/^Step \d+\/\d+：/, "") || "";
  };

  const renderReview = () => {
    if (!reviewSummary) return;
    const payload = collectPayload();
    if (!payload) {
      reviewSummary.innerHTML = "<p>暂无可确认参数。</p>";
      return;
    }
    const contentTypeText = document.querySelector("#contentType option:checked")?.textContent || payload.contentType;
    const postingTimeText = document.querySelector("#postingTime option:checked")?.textContent || payload.postingTime;
    const validAudienceRows = payload.audiences.filter((row) => row.name.trim() && Number(row.ratio) > 0);
    const ratioPercent = Math.round(validAudienceRows.reduce((sum, row) => sum + Number(row.ratio), 0) * 100);
    reviewSummary.innerHTML = `
      <p><strong>内容类型：</strong>${contentTypeText}</p>
      <p><strong>发布时间：</strong>${postingTimeText}</p>
      <p><strong>敏感标签：</strong>${payload.sensitiveTags.length ? payload.sensitiveTags.join("、") : "无"}</p>
      <p><strong>文案长度：</strong>${payload.copyText.length} 字</p>
      <p><strong>有效受众：</strong>${validAudienceRows.length} 类（总占比 ${ratioPercent}%）</p>
      <p><strong>分组方式：</strong>${visibilityPlanLabel(payload.selectedVisibilityPlan)}</p>
      <p><strong>屏蔽人群：</strong>${payload.blockedAudienceNames.length ? payload.blockedAudienceNames.join("、") : "无"}</p>
    `;
  };

  const renderStep = () => {
    stepSections.forEach((section) => {
      const step = Number(section.dataset.stepSection || 1);
      section.hidden = step !== currentStep;
    });
    if (currentStep === 6) renderReview();
    refreshProgress();
  };

  const scheduleDraftSave = () => {
    const payload = collectPayload();
    if (!payload) return;
    if (draftTimer) window.clearTimeout(draftTimer);
    draftTimer = window.setTimeout(() => {
      saveDraft(payload);
      if (draftStatus) draftStatus.textContent = `草稿已自动保存（${formatSavedAt(new Date().toISOString())}）`;
    }, 250);
  };

  const markChanged = () => {
    if (currentStep === 6) renderReview();
    const snapshot = getSnapshot();
    hasUnsubmittedChanges = snapshot !== lastSubmittedSnapshot;
    scheduleDraftSave();
  };

  const goToStep = (targetStep) => {
    if (!canReachStep(targetStep)) return;
    clearError();
    currentStep = Math.max(1, Math.min(TOTAL_STEPS, targetStep));
    renderStep();
  };

  const applyPayloadToForm = (payload) => {
    document.getElementById("contentType").value = payload.contentType || "daily";
    document.getElementById("postingTime").value = payload.postingTime || "daytime";
    document.getElementById("blockedAudienceInput").value = (payload.blockedAudienceNames || []).join(", ");
    document.getElementById("copyText").value = payload.copyText || "";
    document.querySelectorAll("fieldset input[type='checkbox']").forEach((cb) => {
      cb.checked = false;
    });
    (payload.sensitiveTags || []).forEach((tag) => {
      const checkbox = document.querySelector(`fieldset input[value='${tag}']`);
      if (checkbox) checkbox.checked = true;
    });
    audienceBody.innerHTML = "";
    if (payload.audiences?.length) {
      payload.audiences.forEach((row) => createAudienceRow(audienceBody, row, markChanged));
    }
  };

  const bindStepButton = (id, step) => {
    const el = document.getElementById(id);
    el?.addEventListener("click", () => goToStep(step));
  };

  const draft = loadDraft();
  const cached = loadPayload();
  const preferred = draft?.payload || cached;
  if (preferred) {
    applyPayloadToForm(preferred);
    if (draft?.savedAt && draftStatus) {
      draftStatus.textContent = `已自动恢复草稿（${formatSavedAt(draft.savedAt)}）`;
    }
  }

  if (!audienceBody.children.length) {
    createAudienceRow(audienceBody, { name: "家人", ratio: 0.2, audienceType: "family", complexity: "low", inGroup: true }, markChanged);
    createAudienceRow(
      audienceBody,
      { name: "亲密朋友", ratio: 0.3, audienceType: "close_friend", complexity: "low", inGroup: true },
      markChanged
    );
    createAudienceRow(
      audienceBody,
      { name: "同学/同事", ratio: 0.3, audienceType: "classmate_colleague", complexity: "medium", inGroup: true },
      markChanged
    );
    createAudienceRow(
      audienceBody,
      { name: "不熟联系人", ratio: 0.2, audienceType: "acquaintance", complexity: "high", inGroup: false },
      markChanged
    );
  }

  lastSubmittedSnapshot = getSnapshot();
  hasUnsubmittedChanges = false;
  renderStep();

  document.querySelectorAll("#contentType, #postingTime, #blockedAudienceInput, #copyText, fieldset input[type='checkbox']").forEach((el) => {
    el.addEventListener("input", markChanged);
    el.addEventListener("change", markChanged);
  });

  bindStepButton("step1NextBtn", 2);
  bindStepButton("step2PrevBtn", 1);
  bindStepButton("step2NextBtn", 3);
  bindStepButton("step3PrevBtn", 2);
  bindStepButton("step3NextBtn", 4);
  bindStepButton("step4PrevBtn", 3);
  bindStepButton("step4NextBtn", 5);
  bindStepButton("step5PrevBtn", 4);
  bindStepButton("step5NextBtn", 6);
  bindStepButton("step6PrevBtn", 5);

  addAudienceBtn.addEventListener("click", () => {
    createAudienceRow(audienceBody, {}, markChanged);
    markChanged();
  });

  clearDraftBtn?.addEventListener("click", () => {
    clearDraft();
    if (draftStatus) draftStatus.textContent = "草稿已清空。";
  });

  window.addEventListener("beforeunload", (event) => {
    if (!hasUnsubmittedChanges || isNavigating) return;
    event.preventDefault();
    event.returnValue = "你有未提交的参数变更，确认离开吗？";
  });

  startAnalysisBtn.addEventListener("click", () => {
    clearError();
    if (!canReachStep(6)) return;
    const payload = collectPayload();
    if (!payload) return;
    try {
      state.currentPayload = payload;
      savePayload(payload);
      saveDraft(payload);
      lastSubmittedSnapshot = JSON.stringify(payload);
      hasUnsubmittedChanges = false;
      isNavigating = true;
      window.location.href = "/analysis-result";
    } catch {
      showError("保存分析参数失败，请重试。");
    }
  });
}
