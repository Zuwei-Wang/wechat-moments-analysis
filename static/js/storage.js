import { ANALYSIS_PAYLOAD_KEY, COMPARE_SLOTS_KEY } from "./constants.js";

export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

export function normalizePayload(payload) {
  return {
    contentType: payload.contentType || "daily",
    postingTime: payload.postingTime || "daytime",
    selectedVisibilityPlan: payload.selectedVisibilityPlan || "all_visible",
    sensitiveTags: Array.isArray(payload.sensitiveTags) ? payload.sensitiveTags : [],
    blockedAudienceNames: Array.isArray(payload.blockedAudienceNames) ? payload.blockedAudienceNames : [],
    copyText: typeof payload.copyText === "string" ? payload.copyText : "",
    audiences: Array.isArray(payload.audiences) ? payload.audiences : [],
  };
}

export function savePayload(payload) {
  sessionStorage.setItem(ANALYSIS_PAYLOAD_KEY, JSON.stringify(payload));
}

export function loadPayload() {
  const text = sessionStorage.getItem(ANALYSIS_PAYLOAD_KEY);
  if (!text) return null;
  return normalizePayload(JSON.parse(text));
}

export function readCompareSlots() {
  try {
    const raw = localStorage.getItem(COMPARE_SLOTS_KEY);
    if (!raw) return { A: null, B: null };
    const data = JSON.parse(raw);
    return { A: data.A || null, B: data.B || null };
  } catch {
    return { A: null, B: null };
  }
}

export function writeCompareSlots(slots) {
  localStorage.setItem(COMPARE_SLOTS_KEY, JSON.stringify(slots));
}
