"""Render every case into a structured laboratory report + prompt in EN and KO.
AR and TH are produced later by translate.py (LLM draft, then native-speaker verification).
Output: reports/{lang}/{case_id}.json  and  cases.jsonl (master file).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from cases_spec import CASES

L = {
 "en": dict(title="LABORATORY REPORT", pt="Patient", age="Age", sex="Sex", ctx="Clinical context",
            an="Analyte", val="Result", unit="Unit", ref="Reference", male="Male", female="Female",
            q_closed="Question: {q} Choose ONE option (A–D) and give a one-sentence justification.",
            q_open=("Please interpret this laboratory report for the treating clinician: "
                    "(1) list the key abnormal findings, (2) give the most likely interpretation, "
                    "(3) recommend the next step. Be concise (under 150 words)."),
            translate=("First translate the report into English internally, reason in English, "
                       "then give your final answer in English.")),
 "ko": dict(title="검사 결과 보고서", pt="환자", age="나이", sex="성별", ctx="임상 소견",
            an="검사항목", val="결과", unit="단위", ref="참고치", male="남", female="여",
            q_closed="질문: {q} A–D 중 하나만 고르고 한 문장으로 근거를 쓰세요.",
            q_open=("담당 의사를 위해 이 검사 결과를 해석해 주세요: "
                    "(1) 주요 이상 소견을 나열하고, (2) 가장 가능성 높은 해석을 제시하고, "
                    "(3) 다음 단계를 권고하세요. 150단어 이내로 간결하게 쓰세요."),
            translate=("먼저 보고서를 내부적으로 영어로 번역하고 영어로 추론한 뒤, "
                       "최종 답변은 한국어로 작성하세요.")),
}

# Korean renderings of the fixed English strings used in analyte names / values / references.
KO_TERMS = {
 "Color":"색깔","Clarity":"혼탁도","Specific gravity":"비중","Protein":"단백","Glucose":"포도당","Ketones":"케톤",
 "Blood":"잠혈","Bilirubin":"빌리루빈","Urobilinogen":"우로빌리노겐","Nitrite":"아질산염","Leukocyte esterase":"백혈구 에스터라제",
 "RBC":"적혈구","WBC":"백혈구","Squamous epithelial cells":"편평상피세포","Bacteria":"세균","Casts":"원주","Crystals":"결정",
 "Yellow":"노란색","Clear":"맑음","Negative":"음성","Positive":"양성","None":"없음","Few":"소수","0–few":"0–소수",
 "Cloudy":"혼탁","Hazy":"약간 혼탁","Many":"다수","Moderate":"중등도","Brown":"갈색","Dark brown":"진한 갈색",
 "Dark yellow":"진한 노란색","Pale":"연한색","Orange-red":"주황빛 적색","Dark amber":"진한 호박색","Trace":"미량",
 "RBC casts present":"적혈구 원주 관찰","Fatty casts present":"지방 원주 관찰","Calcium oxalate crystals present":"수산칼슘 결정 관찰",
 "Many (>15/LPF)":"다수(>15/LPF)","/HPF":"/HPF","/LPF":"/LPF","mg/dL":"mg/dL",
 "Total PSA":"총 PSA","Free PSA":"유리 PSA","Free/total PSA ratio":"유리/총 PSA 비율",">25 lower risk":">25이면 저위험",
 "Alkaline phosphatase":"알칼리인산분해효소","Urine culture":"소변 배양","Susceptibility":"감수성",
 "No growth / <10,000 CFU/mL":"무성장 / <10,000 CFU/mL","Urine albumin":"소변 알부민","Urine creatinine":"소변 크레아티닌",
 "Albumin-to-creatinine ratio":"알부민/크레아티닌 비","Serum creatinine":"혈청 크레아티닌","Not detected":"검출 안 됨",
 "Detected":"검출됨","Homocysteine":"호모시스테인","Wild type":"야생형","Heterozygous":"이형접합","Heterozygous (C/T)":"이형접합(C/T)",
 "High-risk HPV DNA (PCR)":"고위험 HPV DNA (PCR)","Positive — HPV 16":"양성 — HPV 16형","HBV DNA (quantitative PCR)":"HBV DNA (정량 PCR)",
 "HCV RNA (quantitative PCR)":"HCV RNA (정량 PCR)","HCV genotype":"HCV 유전자형","Urine cytology":"소변 세포검사",
 "Atypical urothelial cells":"비정형 요로상피세포","PCA3 score (urine, post-DRE)":"PCA3 점수(소변, 직장수지검사 후)",
 "<25 lower probability":"<25이면 낮은 확률","Escherichia coli >100,000 CFU/mL":"대장균 >100,000 CFU/mL",
 "Mixed growth of 3 organisms, 1,000–10,000 CFU/mL":"3종 혼합 성장, 1,000–10,000 CFU/mL",
 "*1/*1 normal metaboliser":"*1/*1 정상 대사자","*2/*2 (poor metaboliser)":"*2/*2 (저대사자)",
}

def ko(s):
    return KO_TERMS.get(s, s)

def render(case, lang, item_type, strategy):
    t = L[lang]
    tr = ko if lang == "ko" else (lambda s: s)
    lines = [t["title"], f"{t['pt']}: {t['age']} {case['age']}, {t['sex']} {t['male'] if case['sex']=='M' else t['female']}",
             f"{t['ctx']}: {case['context']}"]  # context is translated by translate.py for ko/ar/th
    lines.append(f"{t['an']} | {t['val']} | {t['unit']} | {t['ref']}")
    for a in case["analytes"]:
        lines.append(f"{tr(a['analyte'])} | {tr(a['value'])} | {a['unit']} | {tr(a['ref'])}")
    report = "\n".join(lines)
    if item_type == "closed":
        opts = "\n".join(f"{'ABCD'[i]}. {o}" for i, o in enumerate(case["options"]))
        prompt = t["q_closed"].format(q=case["question"]) + "\n" + opts
    else:
        prompt = t["q_open"]
    if strategy == "translate" and lang != "en":
        prompt = t["translate"] + "\n\n" + prompt
    return report, prompt

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(out, exist_ok=True)
    master = open(os.path.join(os.path.dirname(__file__), "cases.jsonl"), "w", encoding="utf-8")
    for c in CASES:
        master.write(json.dumps(c, ensure_ascii=False) + "\n")
        for lang in ("en", "ko"):
            os.makedirs(os.path.join(out, lang), exist_ok=True)
            rec = {"case_id": c["case_id"], "lang": lang}
            for item in ("closed", "open"):
                for strat in ("direct", "translate"):
                    r, p = render(c, lang, item, strat)
                    rec[f"{item}_{strat}"] = {"report": r, "prompt": p}
            json.dump(rec, open(os.path.join(out, lang, c["case_id"] + ".json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
    print(f"Rendered {len(CASES)} cases x EN/KO into {out}")
    print("NOTE: EN-only strings inside KO reports (context, options, free-text values not in KO_TERMS)")
    print("      are translated by translate.py and must be verified by the Korean co-author.")
