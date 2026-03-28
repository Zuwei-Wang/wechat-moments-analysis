import { AUDIENCE_TYPE_PROFILE, state } from "./constants.js";
import { loadPayload, savePayload } from "./storage.js";

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

  tr.querySelector("button").addEventListener("click", () => tr.remove());
  tr.querySelector("[name='ratio']").addEventListener("input", (event) => {
    tr.querySelector(".ratio-value").textContent = `${event.target.value}%`;
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
  const blockedAudienceNames = blockedAudienceInput.value.split(",").map((name) => name.trim()).filter(Boolean);
  const copyText = copyTextEl.value.trim();
  const audiences = Array.from(audienceBody.querySelectorAll("tr")).map((row) => {
    const read = (name) => row.querySelector(`[name='${name}']`).value;
    return {
      name: read("name"),
      ratio: Number(read("ratio")) / 100,
      audienceType: read("audienceType"),
      complexity: read("complexity"),
      inGroup: row.querySelector("[name='inGroup']").checked,
    };
  });

  return {
    contentType,
    postingTime,
    selectedVisibilityPlan: "all_visible",
    sensitiveTags,
    blockedAudienceNames,
    copyText,
    audiences,
  };
}

export function initStartPage() {
  const audienceBody = document.getElementById("audienceBody");
  const addAudienceBtn = document.getElementById("addAudience");
  const startAnalysisBtn = document.getElementById("startAnalysisBtn");
  const errorBox = document.getElementById("errorBox");
  if (!audienceBody || !addAudienceBtn || !startAnalysisBtn) return;

  const cached = loadPayload();
  if (cached) {
    document.getElementById("contentType").value = cached.contentType || "daily";
    document.getElementById("postingTime").value = cached.postingTime || "daytime";
    document.getElementById("blockedAudienceInput").value = (cached.blockedAudienceNames || []).join(", ");
    document.getElementById("copyText").value = cached.copyText || "";
    (cached.sensitiveTags || []).forEach((tag) => {
      const checkbox = document.querySelector(`fieldset input[value='${tag}']`);
      if (checkbox) checkbox.checked = true;
    });
    if (cached.audiences?.length) cached.audiences.forEach((row) => createAudienceRow(audienceBody, row));
  }

  if (!audienceBody.children.length) {
    createAudienceRow(audienceBody, { name: "家人", ratio: 0.2, audienceType: "family", complexity: "low", inGroup: true });
    createAudienceRow(audienceBody, { name: "亲密朋友", ratio: 0.3, audienceType: "close_friend", complexity: "low", inGroup: true });
    createAudienceRow(audienceBody, { name: "同学/同事", ratio: 0.3, audienceType: "classmate_colleague", complexity: "medium", inGroup: true });
    createAudienceRow(audienceBody, { name: "不熟联系人", ratio: 0.2, audienceType: "acquaintance", complexity: "high", inGroup: false });
  }

  addAudienceBtn.addEventListener("click", () => createAudienceRow(audienceBody));
  startAnalysisBtn.addEventListener("click", () => {
    if (errorBox) errorBox.hidden = true;
    const payload = collectPayload();
    if (!payload) return;
    try {
      state.currentPayload = payload;
      savePayload(payload);
      window.location.href = "/analysis-result";
    } catch {
      if (errorBox) {
        errorBox.textContent = "保存分析参数失败，请重试。";
        errorBox.hidden = false;
      }
    }
  });
}
