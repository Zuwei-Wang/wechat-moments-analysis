export const ANALYSIS_PAYLOAD_KEY = "moments_analysis_payload";
export const ANALYSIS_DRAFT_KEY = "moments_analysis_draft";
export const COMPARE_SLOTS_KEY = "moments_analysis_compare_slots";
export const DETAIL_PAGE_SIZE = 5;

export const AUDIENCE_TYPE_PROFILE = {
  family: { label: "家人", benefit: 0.52, risk: 0.24 },
  close_friend: { label: "亲密朋友", benefit: 0.78, risk: 0.3 },
  classmate_colleague: { label: "同学/同事", benefit: 0.58, risk: 0.48 },
  acquaintance: { label: "不熟联系人", benefit: 0.32, risk: 0.68 },
  special: { label: "特殊对象", benefit: 0.45, risk: 0.72 },
};

export const state = {
  detailRowsState: [],
  detailCurrentPage: 1,
  currentPayload: null,
  currentResult: null,
};
