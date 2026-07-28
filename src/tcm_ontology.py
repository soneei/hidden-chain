"""
Hidden Chain — TCM Syndrome Ontology (research/014)
====================================================
Pure theory. ZERO HRV dependency.

This module weaves the full TCM "net" that the 5 primary engine axes
(Defined in tcm_theory.py) are only a small, HRV-evidenced subset of.

It organizes ~90 common clinical syndrome patterns along three
orthogonal axes, exactly as a clinician reasons:

  1. 八纲 (Eight Principles)  : yin/yang, exterior/interior,
                                cold/heat, deficiency/excess
  2. 五脏六腑 (Zang-Fu organs): which organ system is failing
  3. 病因 (Etiology)           : 六淫 (six exogenous), 七情 (seven
                                emotions), 饮食劳逸, 病理产物 (phlegm/
                                blood-stasis/food stagnation), etc.

CRITICAL COMPLIANCE NOTE
------------------------
HRV (tcm_hrv_estimator.py) can proxy ONLY a small subset of these
patterns — those with a clear autonomic / vagal signature. Every entry
carries `hrv_detectable` and an `evidence` grade. Entries with
`hrv_detectable = False` are THEORY-ONLY: they are part of the knowledge
net for auditability and future report enrichment, but the engine MUST
NOT score them from HRV. Output framing stays "证候倾向性评估", never
diagnosis. See research/014 and tcm_theory.TCM_DISCLAIMER.

Authority: 规划教材《中医诊断学》《中医基础理论》《中医内科学》。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from tcm_theory import EvidenceGrade


# ──────────────────────────────────────────────
# 受控词表 (controlled vocabularies)
# ──────────────────────────────────────────────
# 八纲：阴阳 表里 寒热 虚实
EIGHT_PRINCIPLES: tuple[str, ...] = (
    "yin", "yang", "exterior", "interior", "cold", "heat", "deficiency", "excess"
)

# 五脏六腑（本项目涉及的脏腑系统）
ZANG_FU_ORGANS: dict[str, dict[str, str]] = {
    "心":   {"en": "Heart",   "role": "主血脉、主神明；HRV 与之相关性最强"},
    "肝":   {"en": "Liver",   "role": "主疏泄、藏血；对应整体气机/自主神经张力"},
    "脾":   {"en": "Spleen",  "role": "主运化、统血；为气血生化之源（后天之本）"},
    "肺":   {"en": "Lung",    "role": "主气司呼吸、通调水道"},
    "肾":   {"en": "Kidney",  "role": "藏精、主水、纳气；阴阳根本"},
    "胃":   {"en": "Stomach", "role": "受纳腐熟，与脾相表里"},
    "小肠": {"en": "Small Intestine", "role": "受盛化物、泌别清浊"},
    "大肠": {"en": "Large Intestine", "role": "传化糟粕"},
    "膀胱": {"en": "Bladder", "role": "贮尿排尿"},
    "胆":   {"en": "Gallbladder", "role": "贮藏排泄胆汁、主决断"},
    "三焦": {"en": "Triple Burner", "role": "气化通路、水液运行"},
}

# 病因（六淫 / 七情 / 饮食劳逸 / 病理产物 / 其他）
ETIOLOGY_FACTORS: dict[str, list[str]] = {
    "六淫": ["风", "寒", "暑", "湿", "燥", "火(热)"],
    "疫疠": ["疫疠"],
    "七情": ["喜", "怒", "忧", "思", "悲", "恐", "惊"],
    "饮食劳逸": ["饮食不节", "劳逸失度", "过劳", "过逸"],
    "病理产物": ["痰饮", "瘀血", "结石", "食滞"],
    "其他": ["外伤", "虫兽所伤", "药邪", "体质", "久病", "失治误治"],
}

# 扁平病因词表（校验用）
ETIOLOGY_ALL: tuple[str, ...] = tuple(
    f for _group, factors in ETIOLOGY_FACTORS.items() for f in factors
)

# 证型大类
CATEGORY_ZANGFU = "zang_fu"            # 脏腑辨证
CATEGORY_QI_BLOOD = "qi_blood_fluid"   # 气血津液辨证
CATEGORY_EXTERIOR = "exterior_pathogen"  # 六淫/外感/卫气营血/六经


@dataclass
class SyndromeCatalogEntry:
    """One common clinical TCM syndrome (教材证型)，纯理论条目。"""
    id: str
    name_cn: str
    name_en: str
    category: str                                # CATEGORY_*
    organ_system: list[str]                      # subset of ZANG_FU_ORGANS keys
    eight_principle: list[str]                   # subset of EIGHT_PRINCIPLES
    etiology: list[str]                          # subset of ETIOLOGY_ALL
    differentiation_points: list[str]            # 辨证要点（教材原汁）
    tongue_pulse: str                            # 舌脉
    patho: str                                   # 病因病机
    hrv_detectable: bool = False                 # HRV 能否代理（仅小子集）
    evidence: EvidenceGrade = EvidenceGrade.NONE  # HRV→证 证据等级
    notes: str = ""                              # 备注（如 HRV 相关性说明）


# ──────────────────────────────────────────────
# 证候目录（~90 条临床常见证型）
#   organ_system / eight_principle / etiology 均取自受控词表
#   hrv_detectable=True 仅限确有自主神经相关证据者
# ──────────────────────────────────────────────
TCM_SYNDROME_CATALOG: dict[str, SyndromeCatalogEntry] = {}


def _add(
    id: str, name_cn: str, name_en: str, category: str,
    organ: list[str], principle: list[str], etiology: list[str],
    diff: list[str], tp: str, patho: str,
    hrv: bool = False, evidence: EvidenceGrade = EvidenceGrade.NONE,
    notes: str = "",
) -> None:
    TCM_SYNDROME_CATALOG[id] = SyndromeCatalogEntry(
        id=id, name_cn=name_cn, name_en=name_en, category=category,
        organ_system=organ, eight_principle=principle, etiology=etiology,
        differentiation_points=diff, tongue_pulse=tp, patho=patho,
        hrv_detectable=hrv, evidence=evidence, notes=notes,
    )


# ══════════════════════════════════════════════
# A. 脏腑辨证（Zang-Fu，按脏腑）
# ══════════════════════════════════════════════

# —— 肝系 (Liver) ——
_add("liver_qi_stagnation", "肝郁气滞", "Liver-Qi Stagnation", CATEGORY_ZANGFU,
     ["肝"], ["excess"], ["怒", "思"],
     ["情志抑郁，善太息", "胸胁、少腹胀闷窜痛", "脉弦"],
     "苔薄白；脉弦", "肝失疏泄，气机郁滞；七情所伤为常见因。",
     hrv=True, evidence=EvidenceGrade.MODERATE,
     notes="HRV 偏低、恢复慢(vagal reactivation 慢)、日间波动大→自主神经张力异常(NRICM 2010)。")
_add("liver_fire_hyperactivity", "肝火炽盛", "Liver-Fire Hyperactivity", CATEGORY_ZANGFU,
     ["肝"], ["excess", "heat"], ["怒", "火(热)"],
     ["头胀痛，面红目赤", "口苦口干，急躁易怒", "舌红苔黄，脉弦数"],
     "舌红苔黄；脉弦数", "肝郁化火或过食辛辣→肝火上炎。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="交感偏亢：RHR↑、HRV↓、应激反应强（强=实火，证据弱）。")
_add("liver_yang_rising", "肝阳上亢", "Liver-Yang Rising", CATEGORY_ZANGFU,
     ["肝", "肾"], ["excess", "heat"], ["怒", "体质", "久病"],
     ["头晕目眩，面红升火", "头重脚轻，腰膝酸软", "脉弦有力"],
     "舌红少苔；脉弦有力", "肝肾阴虚，阴不制阳，肝阳亢逆。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="交感张力高伴血压波动，HRV 降低（证据弱）。")
_add("liver_blood_deficiency", "肝血虚", "Liver-Blood Deficiency", CATEGORY_ZANGFU,
     ["肝"], ["deficiency"], ["久病", "体质"],
     ["爪甲不荣，肢麻", "视力减退，夜盲", "舌淡，脉弦细"],
     "舌淡；脉弦细", "失血或生化不足→肝血亏虚，筋目失养。")
_add("liver_yin_deficiency", "肝阴虚", "Liver-Yin Deficiency", CATEGORY_ZANGFU,
     ["肝"], ["deficiency", "heat"], ["久病", "体质"],
     ["胁肋隐痛，两目干涩", "五心烦热，潮热盗汗", "舌红少津，脉弦细数"],
     "舌红少津，少苔；脉弦细数", "肝肾阴亏，虚热内生。")
_add("liver_gallbladder_damp_heat", "肝胆湿热", "Liver-Gallbladder Damp-Heat", CATEGORY_ZANGFU,
     ["肝", "胆"], ["excess", "heat"], ["湿", "火(热)"],
     ["胁肋胀痛，口苦", "身目发黄，小便黄赤", "舌红苔黄腻，脉弦滑数"],
     "舌红苔黄腻；脉弦滑数", "湿热蕴结肝胆，疏泄失常。")
_add("cold_stagnation_liver_meridian", "寒滞肝脉", "Cold Stagnation in Liver Meridian", CATEGORY_ZANGFU,
     ["肝"], ["excess", "cold"], ["寒"],
     ["少腹、睾丸冷痛坠胀", "遇寒加重，得温则减", "舌淡苔白，脉沉弦或迟"],
     "舌淡苔白；脉沉弦或迟", "寒邪凝滞肝脉，气血不畅。")
_add("liver_wind_yang", "肝阳化风", "Liver-Wind (Yang Collapse)", CATEGORY_ZANGFU,
     ["肝", "肾"], ["excess"], ["体质", "久病"],
     ["眩晕欲仆，头摇", "肢麻震颤，语言謇涩", "舌红苔腻，脉弦有力"],
     "舌红苔腻；脉弦有力", "肝阳亢逆无制，亢极化风（中风先兆）。")
_add("liver_wind_heat", "热极生风", "Liver-Wind (Heat Extremity)", CATEGORY_ZANGFU,
     ["肝"], ["excess", "heat"], ["火(热)", "疫疠"],
     ["高热抽搐，颈项强直", "角弓反张，神昏", "舌红绛，脉弦数"],
     "舌红绛；脉弦数", "邪热亢盛，燔灼肝经，热极生风。")
_add("liver_wind_yin", "阴虚动风", "Liver-Wind (Yin Deficiency)", CATEGORY_ZANGFU,
     ["肝", "肾"], ["deficiency"], ["久病", "体质"],
     ["手足蠕动，低热", "午后颧红，口干咽燥", "舌红少苔，脉弦细数"],
     "舌红少苔；脉弦细数", "肝肾阴亏，筋脉失濡，虚风内动。")
_add("liver_wind_blood", "血虚生风", "Liver-Wind (Blood Deficiency)", CATEGORY_ZANGFU,
     ["肝"], ["deficiency"], ["久病", "体质"],
     ["肢体麻木，筋肉瞤动", "眩晕眼花，爪甲淡白", "舌淡，脉弦细"],
     "舌淡；脉弦细", "肝血不足，筋脉失养，虚风内动。")

# —— 心系 (Heart) ——
_add("heart_qi_deficiency", "心气虚", "Heart-Qi Deficiency", CATEGORY_ZANGFU,
     ["心"], ["deficiency"], ["久病", "体质", "过劳"],
     ["心悸，气短", "神疲乏力，动则尤甚", "舌淡，脉虚"],
     "舌淡；脉虚", "心气不足，鼓动无力。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="HRV 降低、RHR 偏快倾向（心主血脉，证据弱）。")
_add("heart_yang_deficiency", "心阳虚", "Heart-Yang Deficiency", CATEGORY_ZANGFU,
     ["心"], ["deficiency", "cold"], ["久病", "体质"],
     ["心悸怔忡，畏寒肢冷", "胸闷气短，面白", "舌淡胖，脉沉微或结代"],
     "舌淡胖；脉沉微或结代", "心阳不振，温运失职。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="HRV 低、RHR 偏低或正常低值（整体机能低下，证据弱）。")
_add("heart_blood_deficiency", "心血虚", "Heart-Blood Deficiency", CATEGORY_ZANGFU,
     ["心"], ["deficiency"], ["久病", "体质"],
     ["心悸失眠，健忘", "头晕目眩，面色无华", "舌淡，脉细"],
     "舌淡；脉细", "心血亏虚，心神失养。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="HRV 偏低、RHR 偏快（与血虚/气虚相关，证据弱）。")
_add("heart_yin_deficiency", "心阴虚", "Heart-Yin Deficiency", CATEGORY_ZANGFU,
     ["心"], ["deficiency", "heat"], ["久病", "体质"],
     ["心悸心烦，失眠多梦", "口燥咽干，五心烦热", "舌红少津，脉细数"],
     "舌红少津；脉细数", "心阴亏虚，虚火内扰。")
_add("heart_fire_hyperactivity", "心火亢盛", "Heart-Fire Hyperactivity", CATEGORY_ZANGFU,
     ["心"], ["excess", "heat"], ["火(热)", "思", "饮食不节"],
     ["心烦失眠，口舌生疮", "口渴面红，小便黄赤", "舌红苔黄，脉数"],
     "舌红苔黄；脉数", "心火内炽，下移小肠或上炎。")
_add("heart_vessel_blood_stasis", "心脉瘀阻", "Heart-Vessel Blood Stasis", CATEGORY_ZANGFU,
     ["心"], ["excess"], ["瘀血", "体质", "久病"],
     ["心胸憋闷刺痛，固定不移", "面唇青紫", "舌紫暗有瘀斑，脉涩或结代"],
     "舌紫暗有瘀斑；脉涩或结代", "瘀血阻滞心脉，血行不畅。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="HRV 降低、心率变异性减小与心血管自主神经失调相关（证据弱）。")
_add("phlegm_fire_harassing_heart", "痰火扰心", "Phlegm-Fire Harassing Heart", CATEGORY_ZANGFU,
     ["心"], ["excess", "heat"], ["痰饮", "火(热)", "思"],
     ["心烦失眠，易惊", "甚则谵妄神昏，苔黄腻", "舌红苔黄腻，脉滑数"],
     "舌红苔黄腻；脉滑数", "痰郁化火，上扰心神。")
_add("small_intestine_heat", "小肠实热", "Small Intestine Heat", CATEGORY_ZANGFU,
     ["小肠", "心"], ["excess", "heat"], ["火(热)", "饮食不节"],
     ["小便赤涩灼痛", "心烦口渴，口舌生疮", "舌红苔黄，脉数"],
     "舌红苔黄；脉数", "心火下移小肠，分清泌浊失职。")

# —— 脾系 + 胃 (Spleen / Stomach) ——
_add("spleen_qi_deficiency", "脾气虚", "Spleen-Qi Deficiency", CATEGORY_ZANGFU,
     ["脾"], ["deficiency"], ["饮食不节", "劳逸失度", "思"],
     ["食少纳呆，腹胀便溏", "肢体倦怠，神疲乏力", "舌淡苔白，脉缓弱"],
     "舌淡苔白；脉缓弱", "脾失健运，气血生化不足。",
     hrv=True, evidence=EvidenceGrade.MODERATE,
     notes="整体自主神经张力低下：SDNN/HF↓、LF-HF↑、恢复慢(Olivera-Toro 2019)。")
_add("spleen_yang_deficiency", "脾阳虚", "Spleen-Yang Deficiency", CATEGORY_ZANGFU,
     ["脾"], ["deficiency", "cold"], ["饮食不节", "久病"],
     ["腹痛喜温喜按，大便清稀", "畏寒肢冷，面色㿠白", "舌淡胖苔白滑，脉沉迟无力"],
     "舌淡胖苔白滑；脉沉迟无力", "脾阳不足，温运无权，水谷不化。")
_add("spleen_qi_collapse", "脾虚气陷", "Spleen-Qi Collapse (Middle Qi Sinking)", CATEGORY_ZANGFU,
     ["脾"], ["deficiency"], ["过劳", "久病"],
     ["脘腹坠胀，久泻脱肛", "脏器下垂，气短乏力", "舌淡苔白，脉弱"],
     "舌淡苔白；脉弱", "脾虚升举无力，中气下陷。")
_add("spleen_fail_secure_blood", "脾不统血", "Spleen Fail to Secure Blood", CATEGORY_ZANGFU,
     ["脾"], ["deficiency"], ["久病", "体质"],
     ["便血、尿血、肌衄", "面白无华，神疲乏力", "舌淡，脉细弱"],
     "舌淡；脉细弱", "脾气虚衰，统血无权，血溢脉外。")
_add("cold_damp_encumber_spleen", "寒湿困脾", "Cold-Damp Encumbering Spleen", CATEGORY_ZANGFU,
     ["脾"], ["excess", "cold"], ["寒", "湿", "饮食不节"],
     ["脘腹冷痛，泄泻清稀", "恶心呕吐，头身困重", "舌淡胖苔白腻，脉沉迟或濡缓"],
     "舌淡胖苔白腻；脉沉迟或濡缓", "寒湿内盛，脾阳受困，运化失司。")
_add("damp_heat_accumulate_spleen", "湿热蕴脾", "Damp-Heat Accumulating Spleen", CATEGORY_ZANGFU,
     ["脾"], ["excess", "heat"], ["湿", "火(热)", "饮食不节"],
     ["脘腹胀闷，恶心厌油", "身热不扬，大便溏臭", "舌红苔黄腻，脉濡数"],
     "舌红苔黄腻；脉濡数", "湿热蕴结中焦，脾胃升降失常。")
_add("stomach_qi_deficiency", "胃气虚", "Stomach-Qi Deficiency", CATEGORY_ZANGFU,
     ["胃"], ["deficiency"], ["饮食不节", "劳逸失度"],
     ["胃脘隐痛，痞满纳少", "气短乏力，口淡", "舌淡苔白，脉弱"],
     "舌淡苔白；脉弱", "胃气虚弱，受纳腐熟无力。")
_add("stomach_yang_deficiency", "胃阳虚", "Stomach-Yang Deficiency", CATEGORY_ZANGFU,
     ["胃"], ["deficiency", "cold"], ["饮食不节", "久病"],
     ["胃脘冷痛，喜温喜按", "泛吐清水，食少", "舌淡胖，脉沉迟无力"],
     "舌淡胖；脉沉迟无力", "胃阳不足，虚寒内生。")
_add("stomach_yin_deficiency", "胃阴虚", "Stomach-Yin Deficiency", CATEGORY_ZANGFU,
     ["胃"], ["deficiency", "heat"], ["久病", "体质", "燥"],
     ["胃脘灼痛，饥不欲食", "口干咽燥，大便干结", "舌红少津，脉细数"],
     "舌红少津；脉细数", "胃阴亏虚，濡润失职，虚热内生。")
_add("stomach_fire_hyperactivity", "胃火炽盛", "Stomach-Fire Hyperactivity", CATEGORY_ZANGFU,
     ["胃"], ["excess", "heat"], ["火(热)", "饮食不节", "思"],
     ["胃脘灼痛，消谷善饥", "口臭牙龈肿痛，便秘", "舌红苔黄，脉滑数"],
     "舌红苔黄；脉滑数", "胃火炽盛，消腐太过。")
_add("food_stagnation_stomach", "食滞胃脘", "Food Stagnation in Stomach", CATEGORY_ZANGFU,
     ["胃"], ["excess"], ["食滞", "饮食不节"],
     ["脘腹胀满疼痛，嗳腐吞酸", "厌食，泻下臭秽", "苔厚腻，脉滑"],
     "苔厚腻；脉滑", "饮食不节，食积胃脘，腐熟不及。")

# —— 肺系 + 大肠 (Lung / Large Intestine) ——
_add("lung_qi_deficiency", "肺气虚", "Lung-Qi Deficiency", CATEGORY_ZANGFU,
     ["肺"], ["deficiency"], ["久病", "体质", "过劳"],
     ["咳喘无力，气短懒言", "自汗恶风，易感冒", "舌淡苔白，脉虚弱"],
     "舌淡苔白；脉虚弱", "肺气不足，卫外不固，宣降失司。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="自主神经张力低下、RHR 偏快倾向（证据弱）。")
_add("lung_yin_deficiency", "肺阴虚", "Lung-Yin Deficiency", CATEGORY_ZANGFU,
     ["肺"], ["deficiency", "heat"], ["久病", "燥", "体质"],
     ["干咳少痰，痰中带血", "潮热盗汗，口干咽燥", "舌红少津，脉细数"],
     "舌红少津；脉细数", "肺阴亏虚，虚热内生，清肃失司。")
_add("wind_cold_invade_lung", "风寒犯肺", "Wind-Cold Invading Lung", CATEGORY_ZANGFU,
     ["肺"], ["exterior", "cold"], ["风", "寒"],
     ["咳嗽痰稀白，鼻塞流清涕", "恶寒发热，无汗", "苔薄白，脉浮紧"],
     "苔薄白；脉浮紧", "风寒外束，肺卫失宣。")
_add("wind_heat_invade_lung", "风热犯肺", "Wind-Heat Invading Lung", CATEGORY_ZANGFU,
     ["肺"], ["exterior", "heat"], ["风", "火(热)"],
     ["咳嗽痰黄稠，咽喉肿痛", "发热微恶风，有汗", "舌尖红苔薄黄，脉浮数"],
     "舌尖红苔薄黄；脉浮数", "风热犯表，肺失清肃。")
_add("dryness_invade_lung", "燥邪犯肺", "Dryness Invading Lung", CATEGORY_ZANGFU,
     ["肺"], ["exterior", "heat"], ["燥"],
     ["干咳无痰或痰少而黏", "唇鼻干燥，咽喉干痛", "舌红少津，脉浮数或细"],
     "舌红少津；脉浮数或细", "燥邪伤肺，津液受损。")
_add("lung_heat_exuberant", "肺热壅盛", "Lung-Heat Exuberant", CATEGORY_ZANGFU,
     ["肺"], ["excess", "heat"], ["火(热)", "痰饮"],
     ["发热咳嗽，气喘息粗", "胸痛口渴，舌红苔黄", "舌红苔黄，脉数"],
     "舌红苔黄；脉数", "热邪壅肺，肺气上逆。")
_add("phlegm_damp_obstruct_lung", "痰湿阻肺", "Phlegm-Damp Obstructing Lung", CATEGORY_ZANGFU,
     ["肺", "脾"], ["excess"], ["痰饮", "湿"],
     ["咳嗽痰多色白易咯", "胸闷气喘，苔白腻", "舌淡苔白腻，脉滑"],
     "舌淡苔白腻；脉滑", "脾失健运，聚湿成痰，上贮于肺。")
_add("fluid_retain_chest", "饮停胸胁", "Fluid Retention in Chest", CATEGORY_ZANGFU,
     ["肺", "脾"], ["excess"], ["痰饮"],
     ["胸胁胀满，咳唾引痛", "气息短促", "苔白，脉沉弦"],
     "苔白；脉沉弦", "水饮停聚胸胁，气机阻滞。")
_add("large_intestine_damp_heat", "大肠湿热", "Large Intestine Damp-Heat", CATEGORY_ZANGFU,
     ["大肠"], ["excess", "heat"], ["湿", "火(热)", "饮食不节"],
     ["腹痛泄泻，泻下臭秽或痢下赤白", "肛门灼热，里急后重", "舌红苔黄腻，脉滑数"],
     "舌红苔黄腻；脉滑数", "湿热蕴结大肠，传导失常。")
_add("large_intestine_cold_deficiency", "大肠虚寒", "Large Intestine Cold Deficiency", CATEGORY_ZANGFU,
     ["大肠", "脾"], ["deficiency", "cold"], ["寒", "久病"],
     ["久泻久痢，滑脱不禁", "腹隐痛喜温，畏寒", "舌淡苔白，脉沉弱"],
     "舌淡苔白；脉沉弱", "大肠虚寒，固摄无权。")
_add("intestine_dry_fluid_deficiency", "肠燥津亏", "Intestine Dryness (Fluid Deficiency)", CATEGORY_ZANGFU,
     ["大肠"], ["deficiency"], ["燥", "久病", "体质"],
     ["大便干结，数日一行", "口干咽燥，口臭", "舌红少津，脉细涩"],
     "舌红少津；脉细涩", "津液亏虚，大肠失润。")

# —— 肾系 + 膀胱 (Kidney / Bladder) ——
_add("kidney_yang_deficiency", "肾阳虚", "Kidney-Yang Deficiency", CATEGORY_ZANGFU,
     ["肾"], ["deficiency", "cold"], ["久病", "体质", "过劳"],
     ["畏寒肢冷，腰膝酸冷", "阳痿早泄，夜尿频多", "舌淡胖苔白，脉沉弱"],
     "舌淡胖苔白；脉沉弱", "肾阳不足，温煦气化失职。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="整体机能低下：HRV 低、RHR 偏低（证据弱，难区分阴虚/阳虚）。")
_add("kidney_yin_deficiency", "肾阴虚", "Kidney-Yin Deficiency", CATEGORY_ZANGFU,
     ["肾"], ["deficiency", "heat"], ["久病", "体质", "过劳"],
     ["腰膝酸软，眩晕耳鸣", "潮热盗汗，遗精", "舌红少津，脉细数"],
     "舌红少津；脉细数", "肾阴亏虚，虚热内生。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="交感偏亢：RHR↑、应激反应强（证据弱）。")
_add("kidney_essence_insufficiency", "肾精不足", "Kidney-Essence Insufficiency", CATEGORY_ZANGFU,
     ["肾"], ["deficiency"], ["体质", "久病"],
     ["生长发育迟缓/早衰", "腰膝酸软，健忘恍惚", "舌淡，脉弱"],
     "舌淡；脉弱", "肾精亏损，生长发育与生殖失养。")
_add("kidney_qi_unsecured", "肾气不固", "Kidney-Qi Unsecured", CATEGORY_ZANGFU,
     ["肾"], ["deficiency"], ["久病", "体质", "过劳"],
     ["腰膝酸软，小便频数清长", "遗精滑泄，带下清稀", "舌淡苔白，脉沉弱"],
     "舌淡苔白；脉沉弱", "肾气亏虚，封藏固摄无权。")
_add("kidney_fail_grasp_qi", "肾不纳气", "Kidney Fail to Grasp Qi", CATEGORY_ZANGFU,
     ["肾", "肺"], ["deficiency"], ["久病", "体质"],
     ["久病咳喘，呼多吸少", "动则喘甚，汗出", "舌淡苔白，脉沉弱"],
     "舌淡苔白；脉沉弱", "肾虚摄纳无权，气浮于上。")
_add("bladder_damp_heat", "膀胱湿热", "Bladder Damp-Heat", CATEGORY_ZANGFU,
     ["膀胱", "肾"], ["excess", "heat"], ["湿", "火(热)"],
     ["尿频尿急尿痛，小便黄赤", "少腹胀闷", "舌红苔黄腻，脉滑数"],
     "舌红苔黄腻；脉滑数", "湿热下注膀胱，气化不利。")
_add("kidney_deficiency_water_overflow", "肾虚水泛", "Kidney Deficiency Water Overflow", CATEGORY_ZANGFU,
     ["肾", "脾", "肺"], ["deficiency"], ["久病", "痰饮"],
     ["水肿腰以下为甚，尿少", "心悸喘促，畏寒", "舌淡胖苔白滑，脉沉滑"],
     "舌淡胖苔白滑；脉沉滑", "肾阳不足，水液停聚泛滥。")

# —— 脏腑兼证 (Combined organ patterns) ——
_add("heart_lung_qi_deficiency", "心肺气虚", "Heart-Lung Qi Deficiency", CATEGORY_ZANGFU,
     ["心", "肺"], ["deficiency"], ["久病", "过劳", "体质"],
     ["心悸咳喘，气短乏力", "动则尤甚，自汗", "舌淡苔白，脉沉弱或结代"],
     "舌淡苔白；脉沉弱或结代", "心肺两虚，气虚推运无力。")
_add("heart_liver_blood_deficiency", "心肝血虚", "Heart-Liver Blood Deficiency", CATEGORY_ZANGFU,
     ["心", "肝"], ["deficiency"], ["久病", "体质"],
     ["心悸失眠，健忘", "视物模糊，爪甲不荣", "舌淡，脉细"],
     "舌淡；脉细", "心肝同虚，血不濡养。")
_add("spleen_lung_qi_deficiency", "脾肺两虚", "Spleen-Lung Qi Deficiency", CATEGORY_ZANGFU,
     ["脾", "肺"], ["deficiency"], ["久病", "体质"],
     ["食欲不振，腹胀便溏", "咳喘气短，痰多", "舌淡苔白，脉虚弱"],
     "舌淡苔白；脉虚弱", "脾虚生痰，上贮于肺；肺虚及脾。")
_add("lung_spleen_deficiency", "肺脾两虚", "Lung-Spleen Deficiency", CATEGORY_ZANGFU,
     ["肺", "脾"], ["deficiency"], ["久病", "体质"],
     ["神疲乏力，食少便溏", "久咳痰多，气短", "舌淡苔白，脉细弱"],
     "舌淡苔白；脉细弱", "脾为生痰之源，肺为贮痰之器，两虚相兼。")
_add("lung_kidney_yin_deficiency", "肺肾阴虚", "Lung-Kidney Yin Deficiency", CATEGORY_ZANGFU,
     ["肺", "肾"], ["deficiency", "heat"], ["久病", "体质"],
     ["干咳少痰，痰中带血", "腰膝酸软，骨蒸潮热", "舌红少津，脉细数"],
     "舌红少津；脉细数", "肺阴不足及肾，金水两亏。")
_add("liver_fire_invade_lung", "肝火犯肺", "Liver-Fire Invading Lung", CATEGORY_ZANGFU,
     ["肝", "肺"], ["excess", "heat"], ["怒", "火(热)"],
     ["急躁易怒，胸胁灼痛", "咳嗽阵作，痰中带血", "舌红苔薄黄，脉弦数"],
     "舌红苔薄黄；脉弦数", "肝郁化火，上逆犯肺，木火刑金。")
_add("liver_stomach_disharmony", "肝胃不和", "Liver-Stomach Disharmony", CATEGORY_ZANGFU,
     ["肝", "胃"], ["excess"], ["怒", "思", "饮食不节"],
     ["脘胁胀痛，嗳气吞酸", "烦躁易怒，食少", "苔薄黄，脉弦"],
     "苔薄黄；脉弦", "肝失疏泄，犯胃乘土。")
_add("spleen_kidney_yang_deficiency", "脾肾阳虚", "Spleen-Kidney Yang Deficiency", CATEGORY_ZANGFU,
     ["脾", "肾"], ["deficiency", "cold"], ["久病", "体质"],
     ["畏寒肢冷，腰膝冷痛", "久泻久痢，五更泄泻", "舌淡胖苔白滑，脉沉迟无力"],
     "舌淡胖苔白滑；脉沉迟无力", "脾肾阳气俱虚，温运失职。")

# ══════════════════════════════════════════════
# B. 气血津液辨证（Qi-Blood-Fluid）
# ══════════════════════════════════════════════
_add("qi_deficiency", "气虚证", "Qi Deficiency", CATEGORY_QI_BLOOD,
     ["脾", "肺"], ["deficiency"], ["劳逸失度", "久病", "体质"],
     ["神疲乏力，少气懒言", "自汗，舌淡脉虚", "动则诸症加重"],
     "舌淡苔白；脉虚", "先天不足或后天失养，元气亏虚。",
     hrv=True, evidence=EvidenceGrade.MODERATE,
     notes="整体 HRV 低下→推动无力（RMSSD 低于常模可作 proxy，中）。")
_add("qi_collapse", "气陷证", "Qi Collapse (Sinking)", CATEGORY_QI_BLOOD,
     ["脾"], ["deficiency"], ["过劳", "久病"],
     ["坠胀脱垂，久泻", "气短乏力，脏器下垂", "舌淡苔白，脉弱"],
     "舌淡苔白；脉弱", "气虚升举无力，清阳下陷。")
_add("qi_adverse", "气逆证", "Qi Adverse (Reversal)", CATEGORY_QI_BLOOD,
     ["肺", "胃", "肝"], ["excess"], ["怒", "饮食不节", "寒"],
     ["咳嗽喘息/呕恶/嗳气", "头胀痛，面红", "苔薄，脉弦或滑"],
     "苔薄；脉弦或滑", "气机升降失常，逆而上行。")
_add("qi_stagnation", "气滞证", "Qi Stagnation", CATEGORY_QI_BLOOD,
     ["肝", "脾"], ["excess"], ["怒", "思", "体质"],
     ["胀闷疼痛，走窜不定", "嗳气太息，随情绪增减", "脉弦"],
     "苔薄；脉弦", "气机郁滞，运行不畅。",
     hrv=True, evidence=EvidenceGrade.MODERATE,
     notes="HRV 波动大、恢复慢→气机郁滞（证据中）。")
_add("blood_deficiency", "血虚证", "Blood Deficiency", CATEGORY_QI_BLOOD,
     ["心", "肝", "脾"], ["deficiency"], ["久病", "体质"],
     ["面白无华，唇甲淡白", "眩晕心悸，手足麻木", "舌淡，脉细"],
     "舌淡；脉细", "血亏失充，濡养不足。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="RHR 偏快倾向（血虚→代偿，证据弱）。")
_add("blood_stasis", "血瘀证", "Blood Stasis", CATEGORY_QI_BLOOD,
     ["心", "肝"], ["excess"], ["瘀血", "寒", "久病"],
     ["刺痛固定不移，夜间加重", "面色黧黑，唇甲青紫", "舌紫暗有瘀斑，脉涩"],
     "舌紫暗有瘀斑；脉涩", "血行不畅，瘀血内阻。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="HRV 降低与自主神经/血管内皮功能失调相关（证据弱）。")
_add("blood_heat", "血热证", "Blood Heat", CATEGORY_QI_BLOOD,
     ["心", "肝"], ["excess", "heat"], ["火(热)", "体质"],
     ["出血色鲜红，身热", "心烦口渴，面红", "舌红绛，脉数"],
     "舌红绛；脉数", "热入血分，血热妄行。")
_add("blood_cold", "血寒证", "Blood Cold", CATEGORY_QI_BLOOD,
     ["肝", "肾"], ["excess", "cold"], ["寒", "体质"],
     ["手足清冷，肤色青紫", "小腹冷痛，得温则减", "舌淡暗，脉沉迟涩"],
     "舌淡暗；脉沉迟涩", "寒凝血脉，血行迟涩。")
_add("qi_blood_deficiency_syndrome", "气血两虚证", "Qi-Blood Deficiency", CATEGORY_QI_BLOOD,
     ["脾", "心", "肝"], ["deficiency"], ["久病", "体质", "过劳"],
     ["面色淡白或萎黄，神疲乏力", "心悸失眠，头晕目眩", "舌淡嫩，脉细弱"],
     "舌淡嫩，苔薄白；脉细弱", "气血互根失调，生化不足。",
     hrv=True, evidence=EvidenceGrade.MODERATE,
     notes="RMSSD 低 + RHR 偏快 + 睡眠不足→气血濡养不足（中）。")
_add("qi_fail_secure_blood", "气不摄血", "Qi Fail to Secure Blood", CATEGORY_QI_BLOOD,
     ["脾"], ["deficiency"], ["久病", "体质"],
     ["出血色淡质稀，面色无华", "神疲乏力，气短", "舌淡，脉细弱"],
     "舌淡；脉细弱", "气虚统摄无权，血溢脉外。")
_add("qi_follow_blood_collapse", "气随血脱", "Qi Collapse Following Blood", CATEGORY_QI_BLOOD,
     ["心", "脾"], ["deficiency"], ["瘀血", "外伤"],
     ["大出血后面色苍白，大汗", "四肢厥冷，脉微欲绝", "舌淡，脉微欲绝"],
     "舌淡；脉微欲绝", "大量失血，气随血脱（危候）。")
_add("fluid_deficiency", "津液亏虚证", "Fluid Deficiency", CATEGORY_QI_BLOOD,
     ["肺", "胃", "肾"], ["deficiency"], ["燥", "火(热)", "久病"],
     ["口燥咽干，皮肤干瘪", "小便短少，大便干结", "舌红少津，脉细数"],
     "舌红少津；脉细数", "津液耗伤，濡润失职。")
_add("yang_edema", "阳水", "Yang Edema", CATEGORY_QI_BLOOD,
     ["肺", "脾"], ["excess"], ["风", "湿", "饮食不节"],
     ["起病急，眼睑先肿", "小便不利，恶寒发热", "舌淡红苔薄白或黄，脉浮数或滑"],
     "舌淡红苔薄白或黄；脉浮数或滑", "风邪外袭/湿热内盛，水湿泛溢（实）。")
_add("yin_edema", "阴水", "Yin Edema", CATEGORY_QI_BLOOD,
     ["脾", "肾"], ["deficiency"], ["久病", "体质"],
     ["起病缓，足跗先肿", "腰以下肿甚，畏寒", "舌淡胖苔白滑，脉沉迟"],
     "舌淡胖苔白滑；脉沉迟", "脾肾阳气虚衰，水湿停聚（虚）。")
_add("phlegm_pattern", "痰证", "Phlegm Pattern", CATEGORY_QI_BLOOD,
     ["脾", "肺"], ["excess"], ["痰饮", "湿"],
     ["痰多胸闷，苔腻脉滑", "痰核瘰疬，或蒙蔽清窍", "苔腻，脉滑"],
     "苔腻；脉滑", "津聚为痰，随气升降无处不到。",
     hrv=True, evidence=EvidenceGrade.WEAK,
     notes="严重自主神经抑制、周期校准后仍异常波动（Yang 2008，证据弱-中）。")
_add("fluid_retention_pattern", "饮证", "Fluid-Retention Pattern", CATEGORY_QI_BLOOD,
     ["肺", "脾", "肾"], ["excess"], ["痰饮", "寒"],
     ["脘腹满闷，肠鸣漉漉", "或悬饮、溢饮、支饮", "苔白滑，脉沉弦"],
     "苔白滑；脉沉弦", "水液停聚成饮，阻滞气机。")
_add("internal_damp", "内湿证", "Internal Dampness", CATEGORY_QI_BLOOD,
     ["脾"], ["excess"], ["湿", "饮食不节"],
     ["身重困倦，脘痞纳呆", "便溏苔腻，分泌物秽浊", "苔腻，脉濡"],
     "苔腻；脉濡", "脾失健运，湿从内生。")
_add("internal_dryness", "内燥证", "Internal Dryness", CATEGORY_QI_BLOOD,
     ["肺", "胃", "肾"], ["deficiency"], ["燥", "火(热)", "久病"],
     ["皮肤干燥，口干咽燥", "干咳少痰，大便干结", "舌红少津，脉细"],
     "舌红少津；脉细", "津液耗伤，燥邪内生。")

# ══════════════════════════════════════════════
# C. 外感 / 六淫 / 卫气营血 / 六经（Exterior pathogens）
# ══════════════════════════════════════════════
_add("wind_cold_exterior", "风寒表证", "Wind-Cold Exterior", CATEGORY_EXTERIOR,
     ["肺"], ["exterior", "cold"], ["风", "寒"],
     ["恶寒重发热轻，无汗", "头痛身痛，鼻塞流清涕", "苔薄白，脉浮紧"],
     "苔薄白；脉浮紧", "风寒外束肌表，卫阳被郁。")
_add("wind_heat_exterior", "风热表证", "Wind-Heat Exterior", CATEGORY_EXTERIOR,
     ["肺"], ["exterior", "heat"], ["风", "火(热)"],
     ["发热重恶寒轻，有汗", "咽痛口渴，舌尖红", "苔薄黄，脉浮数"],
     "舌尖红苔薄黄；脉浮数", "风热犯表，卫表不和。")
_add("wind_damp_exterior", "风湿表证", "Wind-Damp Exterior", CATEGORY_EXTERIOR,
     ["肺", "脾"], ["exterior"], ["风", "湿"],
     ["身热不扬，关节酸痛", "头重如裹，胸闷", "苔薄白腻，脉浮缓"],
     "苔薄白腻；脉浮缓", "风湿袭表，滞留经络。")
_add("summerheat_damp", "暑湿证", "Summerheat-Damp", CATEGORY_EXTERIOR,
     ["肺", "脾"], ["exterior", "heat"], ["暑", "湿"],
     ["身热汗出，心烦口渴", "胸闷呕恶，身重困倦", "苔黄腻，脉濡数"],
     "苔黄腻；脉濡数", "暑邪夹湿，郁遏气机。")
_add("cold_damp_exterior", "寒湿证", "Cold-Damp", CATEGORY_EXTERIOR,
     ["脾", "肾"], ["excess", "cold"], ["寒", "湿"],
     ["身重关节疼痛，畏寒", "脘腹痞闷，苔白腻", "舌淡胖苔白腻，脉沉缓"],
     "舌淡胖苔白腻；脉沉缓", "寒湿内盛，气机阻滞。")
_add("damp_heat_pattern", "湿热证", "Damp-Heat", CATEGORY_EXTERIOR,
     ["脾", "肝"], ["excess", "heat"], ["湿", "火(热)"],
     ["身热不扬，午后热甚", "口苦尿黄，苔黄腻", "舌红苔黄腻，脉濡数"],
     "舌红苔黄腻；脉濡数", "湿热交蒸，蕴结三焦。")
_add("dryness_exterior", "燥邪犯表", "Dryness Exterior", CATEGORY_EXTERIOR,
     ["肺"], ["exterior", "heat"], ["燥"],
     ["皮肤干燥，口唇干裂", "干咳少痰，咽燥", "舌红少津，脉浮偏数"],
     "舌红少津；脉浮偏数", "燥邪伤津，肺卫失润。")
_add("warm_disease_fire", "温病火(热)证", "Warm-Disease Fire", CATEGORY_EXTERIOR,
     ["心", "肺"], ["excess", "heat"], ["火(热)", "疫疠"],
     ["高热烦渴，面红目赤", "舌红苔黄，脉洪数", "易入营血"],
     "舌红苔黄；脉洪数", "温热之邪，化火伤津。")
_add("defense_phase", "卫分证", "Defense Phase (Wei)", CATEGORY_EXTERIOR,
     ["肺"], ["exterior", "heat"], ["风", "火(热)", "疫疠"],
     ["发热微恶风，口微渴", "舌尖红苔薄白，脉浮数", "温病初起"],
     "舌尖红苔薄白；脉浮数", "温邪犯表，卫气被郁（表热）。")
_add("qi_phase", "气分证", "Qi Phase", CATEGORY_EXTERIOR,
     ["肺", "胃"], ["excess", "heat"], ["火(热)", "疫疠"],
     ["壮热不恶寒，大汗口渴", "面红目赤，苔黄燥", "舌红苔黄，脉洪大"],
     "舌红苔黄；脉洪大", "温邪入里，气分热盛。")
_add("nutrient_phase", "营分证", "Nutrient Phase (Ying)", CATEGORY_EXTERIOR,
     ["心", "肝"], ["excess", "heat"], ["火(热)", "疫疠"],
     ["身热夜甚，心烦不寐", "斑疹隐隐，舌红绛", "舌红绛，脉细数"],
     "舌红绛；脉细数", "热入营分，营阴受损，心神被扰。")
_add("blood_phase", "血分证", "Blood Phase (Xue)", CATEGORY_EXTERIOR,
     ["心", "肝", "肾"], ["excess", "heat"], ["火(热)", "瘀血", "疫疠"],
     ["高热神昏，出血发斑", "抽搐，舌深绛", "舌深绛，脉细数"],
     "舌深绛；脉细数", "热入血分，耗血动血，热极生风。")
_add("shaoyang", "少阳证", "Shaoyang (Half-Exterior-Half-Interior)", CATEGORY_EXTERIOR,
     ["胆"], ["exterior", "interior"], ["风", "寒"],
     ["寒热往来，胸胁苦满", "口苦咽干，默默不欲食", "苔薄白，脉弦"],
     "苔薄白；脉弦", "邪居半表半里，枢机不利。")
_add("taiyang", "太阳病", "Taiyang Disease", CATEGORY_EXTERIOR,
     ["膀胱", "肺"], ["exterior"], ["风", "寒"],
     ["恶寒发热，头项强痛", "脉浮，或汗出或不汗出", "苔薄白"],
     "苔薄白；脉浮", "风寒袭表，太阳经气不利（太阳经证/腑证）。")
_add("yangming", "阳明病", "Yangming Disease", CATEGORY_EXTERIOR,
     ["胃", "大肠"], ["excess", "heat"], ["火(热)", "燥"],
     ["壮热汗出，不恶寒反恶热", "口渴便秘，腹满痛", "舌红苔黄燥，脉洪大或沉实"],
     "舌红苔黄燥；脉洪大或沉实", "里热实证，燥热结于胃肠。")
_add("three_yin_disease", "三阴证", "Three-Yin Disease", CATEGORY_EXTERIOR,
     ["脾", "肾", "肝"], ["deficiency", "cold"], ["寒", "久病"],
     ["但寒不热，四肢厥冷", "下利清谷，脉沉微", "舌淡胖苔白滑"],
     "舌淡胖苔白滑；脉沉微", "邪入三阴，里虚寒证（太阴/少阴/厥阴）。")


# ──────────────────────────────────────────────
# 查询 helper（供报告/审计层调用；不改变引擎评分逻辑）
# ──────────────────────────────────────────────
def all_entries() -> list[SyndromeCatalogEntry]:
    """Return all catalog entries."""
    return list(TCM_SYNDROME_CATALOG.values())


def catalog_by_organ(organ: str) -> list[SyndromeCatalogEntry]:
    """All syndromes involving a given 脏腑 (e.g. '肝')."""
    return [e for e in TCM_SYNDROME_CATALOG.values() if organ in e.organ_system]


def catalog_by_principle(principle: str) -> list[SyndromeCatalogEntry]:
    """All syndromes tagged with a given 八纲 (e.g. 'deficiency')."""
    return [e for e in TCM_SYNDROME_CATALOG.values() if principle in e.eight_principle]


def catalog_by_etiology(factor: str) -> list[SyndromeCatalogEntry]:
    """All syndromes whose 病因 contains a given factor (e.g. '怒')."""
    return [e for e in TCM_SYNDROME_CATALOG.values() if factor in e.etiology]


def catalog_by_category(category: str) -> list[SyndromeCatalogEntry]:
    """All syndromes in a given 大类 (CATEGORY_*)."""
    return [e for e in TCM_SYNDROME_CATALOG.values() if e.category == category]


def hrv_detectable_entries() -> list[SyndromeCatalogEntry]:
    """Syndromes HRV can proxy — the ONLY subset the engine may score."""
    return [e for e in TCM_SYNDROME_CATALOG.values() if e.hrv_detectable]


def get_entry(sid: str) -> Optional[SyndromeCatalogEntry]:
    """Look up one entry by id, or None."""
    return TCM_SYNDROME_CATALOG.get(sid)


def validate_catalog() -> list[str]:
    """Return a list of consistency errors (empty = valid).

    Used by tests and the audit layer to guarantee the net is internally
    consistent: no duplicate ids, all controlled-vocab values valid,
    hrv_detectable implies a non-NONE evidence grade.
    """
    errors: list[str] = []
    seen_ids: set[str] = set()
    valid_organs = set(ZANG_FU_ORGANS.keys())
    valid_etiologies = set(ETIOLOGY_ALL)

    for sid, e in TCM_SYNDROME_CATALOG.items():
        if sid in seen_ids:
            errors.append(f"duplicate id: {sid}")
        seen_ids.add(sid)

        if e.id != sid:
            errors.append(f"id mismatch: key={sid} but entry.id={e.id}")

        for o in e.organ_system:
            if o not in valid_organs:
                errors.append(f"{sid}: invalid organ '{o}'")
        for p in e.eight_principle:
            if p not in EIGHT_PRINCIPLES:
                errors.append(f"{sid}: invalid principle '{p}'")
        for f in e.etiology:
            if f not in valid_etiologies:
                errors.append(f"{sid}: invalid etiology '{f}'")

        if e.category not in (CATEGORY_ZANGFU, CATEGORY_QI_BLOOD, CATEGORY_EXTERIOR):
            errors.append(f"{sid}: invalid category '{e.category}'")

        if e.hrv_detectable and e.evidence == EvidenceGrade.NONE:
            errors.append(f"{sid}: hrv_detectable but evidence=NONE")

        if not e.differentiation_points:
            errors.append(f"{sid}: empty differentiation_points")

    return errors


def catalog_stats() -> dict[str, int]:
    """Summary counts for the CI report / docs."""
    return {
        "total": len(TCM_SYNDROME_CATALOG),
        "hrv_detectable": len(hrv_detectable_entries()),
        "zang_fu": len(catalog_by_category(CATEGORY_ZANGFU)),
        "qi_blood_fluid": len(catalog_by_category(CATEGORY_QI_BLOOD)),
        "exterior_pathogen": len(catalog_by_category(CATEGORY_EXTERIOR)),
    }
