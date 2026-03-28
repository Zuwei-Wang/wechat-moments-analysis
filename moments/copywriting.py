from __future__ import annotations

from typing import Any

from .constants import RISK_DIMENSION_KEYS

EMOTION_KEYWORDS = [
    "崩溃",
    "难受",
    "烦",
    "无语",
    "气死",
    "哭",
    "委屈",
    "激动",
    "太开心",
    "震惊",
    "离谱",
    "emo",
    "破防",
    "心累",
    "压抑",
    "委屈",
    "失眠",
    "焦虑",
    "抑郁",
    "烦躁",
    "心态炸了",
    "气炸了",
    "生气",
    "愤怒",
    "难过",
    "心酸",
    "心疼",
    "泪目",
    "感动",
    "幸福",
    "治愈",
    "太爽了",
    "太绝了",
    "上头",
    "破大防",
    "顶不住",
]

SHOWOFF_KEYWORDS = [
    "第一名",
    "拿奖",
    "升职",
    "加薪",
    "年薪",
    "豪车",
    "名表",
    "大牌",
    "米其林",
    "别墅",
    "赚了",
    "战绩",
    "优秀",
    "全款",
    "提车",
    "新车",
    "购入",
    "入手",
    "毕业即",
    "总包",
    "offer",
    "升职加薪",
    "绩效A",
    "涨薪",
    "奖金到手",
    "年终奖",
    "签约",
    "项目落地",
    "破纪录",
    "冠军",
    "榜一",
    "爆单",
    "财富自由",
    "买房",
    "新房",
    "大平层",
    "海景房",
    "私厨",
    "商务舱",
    "头等舱",
    "五星级",
    "奢牌",
    "限量款",
    "买买买",
]

PRIVACY_KEYWORDS = [
    "定位",
    "地址",
    "小区",
    "公司",
    "工位",
    "航班",
    "车牌",
    "身份证",
    "病历",
    "孩子",
    "学校",
    "行程",
    "酒店",
    "机场",
    "高铁",
    "动车",
    "登机",
    "航站楼",
    "房间号",
    "门牌",
    "门禁",
    "手机号",
    "电话",
    "微信号",
    "身份证号",
    "证件",
    "银行卡",
    "车位",
    "车库",
    "公司楼层",
    "会议室",
    "单位",
    "科室",
    "病房",
    "住址",
    "户口",
    "学号",
    "班级群",
    "幼儿园",
    "小学",
    "中学",
    "打卡地",
]

TAG_KEYWORDS = {
    "money": [
        "赚了",
        "工资",
        "月薪",
        "年薪",
        "奖金",
        "年终奖",
        "分红",
        "理财",
        "收益",
        "利润",
        "回本",
        "消费",
        "花了",
        "转账",
        "买房",
        "全款",
        "加薪",
        "涨薪",
        "升职",
    ],
    "emotion": [
        "崩溃",
        "难受",
        "心累",
        "焦虑",
        "烦躁",
        "破防",
        "委屈",
        "压抑",
        "生气",
        "愤怒",
        "伤心",
        "开心",
        "激动",
        "幸福",
        "感动",
        "emo",
    ],
    "relationship": [
        "前任",
        "对象",
        "恋爱",
        "分手",
        "暧昧",
        "婚姻",
        "结婚",
        "离婚",
        "冷战",
        "吵架",
        "和好",
        "异地",
    ],
    "location": [
        "定位",
        "地址",
        "住址",
        "小区",
        "门牌",
        "酒店",
        "机场",
        "高铁",
        "航班",
        "行程",
        "打卡地",
        "公司楼层",
        "会议室",
    ],
    "politics": ["政策", "政治", "投票", "立场", "时政", "体制"],
    "work_confidential": [
        "甲方",
        "乙方",
        "客户名单",
        "报价单",
        "合同",
        "机密",
        "保密",
        "项目细节",
        "代码库",
        "内网",
        "财报",
        "商业计划",
    ],
    "health": [
        "病历",
        "住院",
        "体检",
        "治疗",
        "诊断",
        "药",
        "复诊",
        "手术",
        "检查结果",
        "过敏",
    ],
    "family_conflict": ["家庭矛盾", "家里吵", "吵架", "婆媳", "闹翻", "冷暴力", "亲戚矛盾"],
    "children": ["孩子", "娃", "宝宝", "幼儿园", "小学", "学校", "班级", "学号"],
    "appearance": ["体重", "颜值", "减肥", "身材", "变美", "变瘦", "素颜", "医美"],
    "luxury": ["豪车", "名表", "奢侈", "奢牌", "大牌", "包包", "高定", "限量", "五星级", "头等舱"],
    "complaint": ["吐槽", "无语", "离谱", "太差", "烦死", "崩溃", "受不了", "坑", "摆烂"],
}


def _intensity_score(text: str, keywords: list[str], saturation_hits: int = 8) -> float:
    hits = 0
    for kw in keywords:
        if kw in text:
            hits += 1
    if saturation_hits <= 0:
        return 0.0
    return min(1.0, hits / saturation_hits)


def _to_level(score: float) -> str:
    if score >= 0.67:
        return "high"
    if score >= 0.34:
        return "medium"
    return "low"


def analyze_copy_text(text: str) -> dict[str, Any]:
    normalized = (text or "").strip().lower()
    emotion_score = round(_intensity_score(normalized, EMOTION_KEYWORDS), 4)
    showoff_score = round(_intensity_score(normalized, SHOWOFF_KEYWORDS), 4)
    privacy_score = round(_intensity_score(normalized, PRIVACY_KEYWORDS), 4)

    detected_tags: list[str] = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(kw in normalized for kw in keywords):
            detected_tags.append(tag)

    dimension_boost = {
        "misunderstanding": round(min(0.25, emotion_score * 0.14 + showoff_score * 0.08), 4),
        "relationship": round(min(0.25, showoff_score * 0.16 + emotion_score * 0.06), 4),
        "privacy": round(min(0.25, privacy_score * 0.22), 4),
    }
    for dim in RISK_DIMENSION_KEYS:
        dimension_boost.setdefault(dim, 0.0)

    return {
        "textLength": len(normalized),
        "emotionIntensity": {"score": emotion_score, "level": _to_level(emotion_score)},
        "showoffIntensity": {"score": showoff_score, "level": _to_level(showoff_score)},
        "privacyIntensity": {"score": privacy_score, "level": _to_level(privacy_score)},
        "detectedTags": detected_tags,
        "dimensionBoost": dimension_boost,
    }
