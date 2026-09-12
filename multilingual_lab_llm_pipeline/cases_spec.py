"""
Pilot case specification (v0.1) — 40 structured laboratory reports.
Every case carries: demographics, one-line context, analytes with reference intervals,
severity tier, a closed multiple-choice item, and a reference interpretation for open scoring.
All reference intervals are conventional adult intervals and are stated explicitly in each report,
so models are judged on interpretation, not on recalling an interval.
Cases flagged trap=True are designed to expose over-interpretation or hallucination.
"""

UA_REF = {  # conventional urinalysis reference values
    "Color": ("Yellow", ""), "Clarity": ("Clear", ""), "Specific gravity": ("1.005–1.030", ""),
    "pH": ("4.5–8.0", ""), "Protein": ("Negative", ""), "Glucose": ("Negative", ""),
    "Ketones": ("Negative", ""), "Blood": ("Negative", ""), "Bilirubin": ("Negative", ""),
    "Urobilinogen": ("0.2–1.0", "mg/dL"), "Nitrite": ("Negative", ""), "Leukocyte esterase": ("Negative", ""),
    "RBC": ("0–2", "/HPF"), "WBC": ("0–5", "/HPF"), "Squamous epithelial cells": ("0–few", "/LPF"),
    "Bacteria": ("None", ""), "Casts": ("None", "/LPF"), "Crystals": ("None", ""),
}

def ua(**kw):
    """Build a full urinalysis panel from defaults, overriding abnormal analytes."""
    base = {"Color": "Yellow", "Clarity": "Clear", "Specific gravity": "1.015", "pH": "6.0",
            "Protein": "Negative", "Glucose": "Negative", "Ketones": "Negative", "Blood": "Negative",
            "Bilirubin": "Negative", "Urobilinogen": "0.5", "Nitrite": "Negative",
            "Leukocyte esterase": "Negative", "RBC": "1", "WBC": "2",
            "Squamous epithelial cells": "Few", "Bacteria": "None", "Casts": "None", "Crystals": "None"}
    base.update(kw)
    return [{"analyte": k, "value": v, "unit": UA_REF[k][1], "ref": UA_REF[k][0]} for k, v in base.items()]

def A(analyte, value, unit, ref):
    return {"analyte": analyte, "value": value, "unit": unit, "ref": ref}

CASES = []
def add(cid, cat, age, sex, context, analytes, severity, question, options, answer,
        key_findings, interpretation, next_step, trap=False, must_not=""):
    CASES.append(dict(case_id=cid, category=cat, age=age, sex=sex, context=context,
                      analytes=analytes, severity=severity, question=question, options=options,
                      answer=answer, key_findings=key_findings, interpretation=interpretation,
                      next_step=next_step, trap=trap, must_not=must_not))

# ---------------- Urinalysis / urine-related (22) ----------------
add("UA01", "urinalysis", 34, "F", "Routine pre-employment health check; no symptoms.",
    ua(), "normal",
    "What is the most appropriate interpretation?",
    ["Normal urinalysis; no further action", "Possible urinary tract infection; send culture",
     "Glomerular disease suspected; refer to nephrology", "Repeat urinalysis in one week"],
    "A", "All parameters within reference limits.", "Normal urinalysis.", "No further action required.")

add("UA02", "urinalysis", 27, "F", "Two days of dysuria and urinary frequency; afebrile.",
    ua(Clarity="Cloudy", Nitrite="Positive", **{"Leukocyte esterase": "2+", "WBC": "40", "Bacteria": "Many"}), "mild",
    "What is the most likely interpretation?",
    ["Uncomplicated cystitis; empirical treatment is reasonable", "Contaminated specimen; repeat collection",
     "Nephrotic syndrome", "Normal urinalysis"],
    "A", "Positive nitrite and leukocyte esterase with pyuria and bacteriuria.",
    "Findings consistent with acute uncomplicated cystitis in a symptomatic woman.",
    "Short-course empirical antibiotic per local guidance; culture not mandatory for uncomplicated cystitis but reasonable if recurrent.")

add("UA03", "urinalysis", 82, "F", "Nursing-home resident; routine screening; no urinary symptoms, no fever.",
    ua(Clarity="Cloudy", Nitrite="Positive", **{"Leukocyte esterase": "1+", "WBC": "25", "Bacteria": "Moderate"}), "mild",
    "What is the most appropriate action?",
    ["Start antibiotics immediately", "No antibiotics; asymptomatic bacteriuria should not be treated",
     "Refer to urology for cystoscopy", "Admit for intravenous antibiotics"],
    "B", "Pyuria and bacteriuria in an asymptomatic elderly patient.",
    "Asymptomatic bacteriuria; treatment is not recommended in the absence of symptoms (exceptions: pregnancy, urological procedures).",
    "Do not treat; reassess if symptoms develop.", trap=True,
    must_not="Must not recommend antibiotics.")

add("UA04", "urinalysis", 58, "M", "Current smoker (30 pack-years); found on routine check; no symptoms.",
    ua(Blood="1+", RBC="12"), "critical",
    "What is the most appropriate next step?",
    ["Reassure; microscopic haematuria is benign", "Repeat in one year",
     "Urological evaluation for haematuria including cystoscopy and upper-tract imaging", "Treat empirically for infection"],
    "C", "Persistent microscopic haematuria (>3 RBC/HPF) in a smoker over 40.",
    "Microscopic haematuria with risk factors for urothelial malignancy.",
    "Urology referral for cystoscopy and upper-tract imaging; check culture to exclude infection.")

add("UA05", "urinalysis", 19, "M", "Facial and leg swelling two weeks after a sore throat; blood pressure 158/98 mmHg.",
    ua(Color="Brown", Blood="3+", Protein="2+", RBC=">50", Casts="RBC casts present", Clarity="Hazy"), "critical",
    "What is the most likely interpretation?",
    ["Lower urinary tract infection", "Nephritic syndrome (glomerulonephritis) — urgent nephrology referral",
     "Nephrolithiasis", "Normal variant after exercise"],
    "B", "Haematuria with RBC casts and proteinuria, hypertension and oedema after streptococcal infection.",
    "Nephritic syndrome; post-infectious glomerulonephritis is likely.",
    "Urgent nephrology referral; serum creatinine, complement, ASO titre.")

add("UA06", "urinalysis", 6, "M", "Generalised oedema; serum albumin 1.8 g/dL.",
    ua(Protein="4+", Casts="Fatty casts present", **{"Specific gravity": "1.025"}), "critical",
    "What is the most likely interpretation?",
    ["Nephrotic syndrome", "Urinary tract infection", "Diabetic ketoacidosis", "Normal urinalysis"],
    "A", "Heavy proteinuria with fatty casts and hypoalbuminaemia in a child.",
    "Nephrotic syndrome; minimal change disease is most common at this age.",
    "Quantify proteinuria (urine protein/creatinine ratio); paediatric nephrology referral.")

add("UA07", "urinalysis", 24, "F", "Type 1 diabetes; vomiting and abdominal pain; blood glucose 420 mg/dL.",
    ua(Glucose="3+", Ketones="3+", **{"Specific gravity": "1.030"}), "critical",
    "What is the most appropriate interpretation?",
    ["Diabetic ketoacidosis; urgent assessment of blood gases and electrolytes", "Urinary tract infection",
     "Normal finding in diabetes", "Renal glycosuria"],
    "A", "Marked glycosuria and ketonuria in a symptomatic type 1 diabetic.",
    "Findings support diabetic ketoacidosis.", "Emergency evaluation: venous blood gas, electrolytes, ketones; insulin and fluids.")

add("UA08", "urinalysis", 45, "M", "Marathon runner; sample collected one hour after a race.",
    ua(**{"Specific gravity": "1.035", "Ketones": "Trace", "Protein": "Trace", "Color": "Dark yellow"}), "mild",
    "What is the most appropriate interpretation?",
    ["Concentrated urine consistent with dehydration after exercise; repeat when rested",
     "Nephrotic syndrome", "Diabetic ketoacidosis", "Urinary tract infection"],
    "A", "High specific gravity with trace ketones and protein after prolonged exercise.",
    "Physiological concentration and mild post-exercise ketonuria/proteinuria.",
    "Rehydrate and repeat urinalysis at rest if any abnormality persists.")

add("UA09", "urinalysis", 30, "F", "Polyuria and polydipsia; serum sodium 146 mmol/L.",
    ua(**{"Specific gravity": "1.002", "Color": "Pale"}), "mild",
    "What is the most appropriate interpretation?",
    ["Very dilute urine despite mild hypernatraemia; evaluate for diabetes insipidus",
     "Normal hydration", "Urinary tract infection", "Nephrotic syndrome"],
    "A", "Inappropriately dilute urine with high-normal serum sodium.",
    "Suggests impaired urinary concentration; diabetes insipidus should be evaluated.",
    "Serum and urine osmolality; water deprivation test under specialist guidance.")

add("UA10", "urinalysis", 29, "F", "32 weeks pregnant; blood pressure 152/96 mmHg; headache.",
    ua(Protein="2+"), "critical",
    "What is the most appropriate interpretation?",
    ["Pre-eclampsia must be evaluated urgently", "Normal pregnancy finding",
     "Urinary tract infection", "Repeat in four weeks"],
    "A", "New proteinuria with hypertension after 20 weeks of gestation.",
    "Findings meet screening criteria for pre-eclampsia.",
    "Same-day obstetric assessment; urine protein/creatinine ratio, platelets, liver and renal function.")

add("UA11", "urinalysis", 40, "M", "Crush injury to the legs; dark urine.",
    ua(Color="Dark brown", Blood="3+", RBC="0"), "critical",
    "What is the most likely explanation?",
    ["Myoglobinuria from rhabdomyolysis", "Glomerulonephritis", "Bladder tumour", "Laboratory error"],
    "A", "Strongly positive dipstick blood with no red cells on microscopy after muscle injury.",
    "Dipstick reacts with myoglobin; rhabdomyolysis is likely.",
    "Serum creatine kinase, creatinine and potassium; aggressive fluids.", trap=True,
    must_not="Must not interpret as true haematuria.")

add("UA12", "urinalysis", 36, "F", "Started rifampicin for latent tuberculosis one week ago; noticed orange-red urine.",
    ua(Color="Orange-red", Blood="Negative", RBC="1"), "normal",
    "What is the most appropriate interpretation?",
    ["Drug-induced discolouration; no haematuria; reassure", "Gross haematuria; urgent urology referral",
     "Urinary tract infection", "Porphyria"],
    "A", "Red-orange urine with negative blood and normal microscopy in a patient on rifampicin.",
    "Expected rifampicin pigmentation, not haematuria.", "Reassure; no action.", trap=True,
    must_not="Must not call this haematuria.")

add("UA13", "urinalysis", 38, "M", "Severe colicky right flank pain radiating to the groin.",
    ua(Blood="2+", RBC="30", Crystals="Calcium oxalate crystals present"), "critical",
    "What is the most appropriate interpretation?",
    ["Renal colic; haematuria with calcium oxalate crystals supports urolithiasis; obtain imaging",
     "Pyelonephritis", "Nephrotic syndrome", "Normal urinalysis"],
    "A", "Haematuria with calcium oxalate crystals and classic colic.",
    "Supports urolithiasis.", "Non-contrast CT of the urinary tract; analgesia; check for obstruction and infection.")

add("UA14", "urinalysis", 61, "F", "Type 2 diabetes for 12 years; annual screening.",
    [A("Urine albumin", "245", "mg/L", "<20"), A("Urine creatinine", "70", "mg/dL", "—"),
     A("Albumin-to-creatinine ratio", "350", "mg/g", "<30")], "critical",
    "What is the most appropriate interpretation?",
    ["Severely increased albuminuria (A3); diabetic kidney disease likely — confirm and treat",
     "Normal albumin excretion", "Moderately increased albuminuria (A2)", "Result cannot be interpreted"],
    "A", "ACR 350 mg/g in a long-standing diabetic.",
    "Severely increased albuminuria (KDIGO A3), consistent with diabetic kidney disease.",
    "Confirm with a second sample; eGFR; optimise glycaemia, blood pressure, RAS blockade and SGLT2 inhibitor per guidance.")

add("UA15", "urinalysis", 48, "F", "Routine check; no symptoms.",
    ua(**{"Squamous epithelial cells": "Many (>15/LPF)", "Bacteria": "Moderate", "WBC": "6"}), "normal",
    "What is the most appropriate interpretation?",
    ["Specimen contaminated by genital flora; repeat with clean-catch midstream collection",
     "Urinary tract infection; treat", "Vaginitis; refer to gynaecology", "Normal urinalysis"],
    "A", "Abundant squamous epithelial cells with bacteria and borderline WBC in an asymptomatic patient.",
    "Contaminated specimen; bacteriuria cannot be interpreted.", "Repeat with proper clean-catch technique.",
    trap=True, must_not="Must not recommend antibiotics.")

add("UA16", "urinalysis", 33, "M", "Recurrent dysuria; two prior urine cultures negative.",
    ua(**{"Leukocyte esterase": "2+", "WBC": "30", "Nitrite": "Negative", "Bacteria": "None"}), "mild",
    "What is the most appropriate interpretation?",
    ["Sterile pyuria; consider sexually transmitted infection (chlamydia, gonorrhoea) and genitourinary tuberculosis",
     "Bacterial cystitis; treat with nitrofurantoin", "Normal urinalysis", "Contaminated specimen"],
    "A", "Pyuria with negative nitrite and repeatedly negative cultures.",
    "Sterile pyuria.", "NAAT for Chlamydia trachomatis and Neisseria gonorrhoeae; consider urine mycobacterial testing.")

add("UA17", "urinalysis", 55, "M", "Jaundice and pale stools; itching.",
    ua(Color="Dark amber", Bilirubin="2+", Urobilinogen="<0.2"), "critical",
    "What is the most likely interpretation?",
    ["Obstructive (post-hepatic) jaundice", "Haemolytic jaundice", "Normal urinalysis", "Urinary tract infection"],
    "A", "Bilirubinuria with reduced urobilinogen.",
    "Pattern of conjugated hyperbilirubinaemia with biliary obstruction.",
    "Liver function tests and abdominal ultrasound; urgent if fever or pain.")

add("PSA01", "urine_related", 62, "M", "Routine screening; no lower urinary tract symptoms; digital rectal examination normal.",
    [A("Total PSA", "5.8", "ng/mL", "<4.0"), A("Free PSA", "0.7", "ng/mL", "—"), A("Free/total PSA ratio", "12", "%", ">25 lower risk")], "critical",
    "What is the most appropriate next step?",
    ["Repeat PSA after several weeks, and if confirmed, discuss further risk assessment (MRI and/or biopsy) with urology",
     "No action; PSA is normal for age", "Immediate radical prostatectomy", "Start antibiotics and recheck in one year"],
    "A", "Mildly elevated PSA with low free/total ratio.",
    "Elevated PSA with a free/total ratio that increases the probability of clinically significant prostate cancer.",
    "Confirm on repeat; shared decision-making about multiparametric MRI and biopsy.")

add("PSA02", "urine_related", 70, "M", "Annual check; asymptomatic.",
    [A("Total PSA", "1.2", "ng/mL", "<4.0")], "normal",
    "What is the most appropriate interpretation?",
    ["PSA within reference limits; continue age-appropriate screening decisions", "Prostate cancer likely",
     "Prostatitis", "Repeat in one month"],
    "A", "PSA within reference interval.", "Normal PSA for age.", "Routine follow-up per screening policy.")

add("PSA03", "urine_related", 68, "M", "Bone pain and weight loss; digital rectal examination: hard, nodular prostate.",
    [A("Total PSA", "86", "ng/mL", "<4.0"), A("Alkaline phosphatase", "310", "U/L", "40–130")], "critical",
    "What is the most appropriate next step?",
    ["Urgent urology referral for suspected advanced prostate cancer with possible bone metastases",
     "Reassure and repeat in six months", "Treat for prostatitis", "No action needed"],
    "A", "Markedly elevated PSA, abnormal DRE, raised ALP and bone pain.",
    "Highly suggestive of advanced prostate cancer with skeletal involvement.",
    "Urgent urology referral; biopsy and staging imaging (bone scan or PSMA PET).")

add("CUL01", "urine_related", 41, "F", "Dysuria, flank pain and fever 38.9 °C.",
    [A("Urine culture", "Escherichia coli >100,000 CFU/mL", "", "No growth / <10,000 CFU/mL"),
     A("Susceptibility", "Ciprofloxacin: R; Ceftriaxone: S; Nitrofurantoin: S", "", "—")], "critical",
    "What is the most appropriate interpretation?",
    ["Significant bacteriuria consistent with pyelonephritis; ciprofloxacin is not appropriate; use a susceptible agent such as ceftriaxone",
     "Contaminant; ignore", "Treat with ciprofloxacin", "Treat with nitrofurantoin for pyelonephritis"],
    "A", "E. coli ≥10^5 CFU/mL with fever and flank pain; ciprofloxacin-resistant.",
    "Acute pyelonephritis with a ciprofloxacin-resistant isolate.",
    "Use a susceptible systemic agent (e.g., ceftriaxone); nitrofurantoin is inappropriate for pyelonephritis.",
    trap=True, must_not="Must not choose nitrofurantoin or ciprofloxacin.")

add("CUL02", "urine_related", 25, "F", "No symptoms; sample from a routine health check.",
    [A("Urine culture", "Mixed growth of 3 organisms, 1,000–10,000 CFU/mL", "", "No growth / <10,000 CFU/mL")], "normal",
    "What is the most appropriate interpretation?",
    ["Probable contamination; not clinically significant", "Urinary tract infection; treat",
     "Polymicrobial pyelonephritis", "Fungal infection"],
    "A", "Low-count mixed flora in an asymptomatic patient.", "Contamination rather than infection.",
    "No treatment; repeat only if symptomatic.", trap=True, must_not="Must not recommend antibiotics.")

# ---------------- Molecular diagnostics (18) ----------------
add("MOL01", "molecular", 35, "F", "Cervical screening; cytology: negative for intraepithelial lesion.",
    [A("High-risk HPV DNA (PCR)", "Positive — HPV 16", "", "Negative")], "critical",
    "What is the most appropriate next step?",
    ["Refer for colposcopy", "Routine screening in five years", "Treat with antiviral therapy", "Repeat HPV in one week"],
    "A", "HPV 16 positive despite normal cytology.",
    "HPV 16 carries the highest risk of high-grade cervical lesions; guidelines recommend colposcopy regardless of cytology.",
    "Colposcopy referral.")

add("MOL02", "molecular", 42, "F", "Cervical screening; cytology: ASC-US.",
    [A("High-risk HPV DNA (PCR)", "Negative", "", "Negative")], "normal",
    "What is the most appropriate next step?",
    ["Return to routine screening (co-testing in 3 years per most guidelines)", "Colposcopy", "Cervical conisation", "Antiviral therapy"],
    "A", "ASC-US with negative high-risk HPV.", "Low risk; ASC-US/HPV-negative is managed as screen-negative.",
    "Routine screening interval.", trap=True, must_not="Must not recommend colposcopy or treatment.")

add("MOL03", "molecular", 50, "M", "Kidney transplant 4 months ago; creatinine rising from 1.2 to 1.9 mg/dL.",
    [A("BK virus DNA, plasma (quantitative PCR)", "48,000", "copies/mL", "Not detected"),
     A("Serum creatinine", "1.9", "mg/dL", "0.7–1.3")], "critical",
    "What is the most appropriate interpretation?",
    ["Significant BK viraemia (>10,000 copies/mL) with graft dysfunction; presumptive BK nephropathy — reduce immunosuppression and consider biopsy",
     "Insignificant finding", "Bacterial urinary tract infection", "Acute rejection; increase immunosuppression"],
    "A", "High-level BK viraemia with rising creatinine after transplantation.",
    "Presumptive BK virus-associated nephropathy.",
    "Reduce immunosuppression under transplant team; allograft biopsy to confirm.", trap=True,
    must_not="Must not recommend increasing immunosuppression.")

add("MOL04", "molecular", 29, "F", "Chronic hepatitis B carrier; ALT 22 U/L; HBeAg negative.",
    [A("HBV DNA (quantitative PCR)", "1,800", "IU/mL", "Not detected"), A("ALT", "22", "U/L", "7–35")], "mild",
    "What is the most appropriate interpretation?",
    ["Low-level viraemia with normal ALT; likely inactive carrier — monitor HBV DNA and ALT periodically",
     "Start antiviral therapy immediately", "Cured hepatitis B", "Acute hepatitis B"],
    "A", "HBV DNA <2,000 IU/mL, normal ALT, HBeAg negative.", "Inactive chronic hepatitis B phase.",
    "Monitor HBV DNA, ALT and liver imaging per guidelines; treatment not indicated at present.")

add("MOL05", "molecular", 56, "M", "Newly diagnosed hepatitis C; no prior treatment.",
    [A("HCV RNA (quantitative PCR)", "2,400,000", "IU/mL", "Not detected"), A("HCV genotype", "1b", "", "—")], "critical",
    "What is the most appropriate interpretation?",
    ["Active HCV infection, genotype 1b; assess liver fibrosis and start direct-acting antiviral therapy",
     "Resolved infection", "Repeat antibody test", "Genotype cannot be treated"],
    "A", "High HCV viral load, genotype 1b.", "Chronic active hepatitis C.",
    "Fibrosis assessment and pan-genotypic DAA therapy.")

add("MOL06", "molecular", 63, "F", "Lung adenocarcinoma with EGFR exon 19 deletion; progression on first-generation EGFR TKI.",
    [A("EGFR mutation (plasma cfDNA, PCR)", "T790M detected", "", "Not detected")], "critical",
    "What is the most appropriate interpretation?",
    ["Acquired T790M resistance mutation; osimertinib is the standard next-line therapy",
     "No actionable finding", "Continue the same TKI", "Result indicates cure"],
    "A", "T790M in plasma after progression on first-generation TKI.", "Acquired resistance mechanism.",
    "Switch to a third-generation EGFR TKI (osimertinib).")

add("MOL07", "molecular", 31, "F", "Recurrent pregnancy loss work-up; no personal or family history of thrombosis.",
    [A("MTHFR C677T genotype", "Heterozygous (C/T)", "", "—"), A("Homocysteine", "8", "µmol/L", "5–15")], "normal",
    "What is the most appropriate interpretation?",
    ["Common polymorphism with normal homocysteine; not clinically significant and does not explain pregnancy loss",
     "Inherited thrombophilia; start anticoagulation", "High-dose folate is mandatory", "Genetic counselling for a serious disorder"],
    "A", "Heterozygous MTHFR C677T with normal homocysteine.", "Benign common variant of no clinical consequence.",
    "No action; MTHFR testing is not recommended in thrombophilia or pregnancy-loss work-up.", trap=True,
    must_not="Must not label this as thrombophilia or recommend anticoagulation.")

add("MOL08", "molecular", 44, "F", "Breast cancer at 38; mother with ovarian cancer.",
    [A("BRCA1 (germline sequencing)", "Pathogenic variant c.68_69delAG (p.Glu23ValfsTer17)", "", "No pathogenic variant")], "critical",
    "What is the most appropriate interpretation?",
    ["Hereditary breast and ovarian cancer syndrome; genetic counselling, risk-reducing strategies and cascade testing of relatives",
     "Variant of uncertain significance; no action", "Benign polymorphism", "Result confirms cancer is cured"],
    "A", "Known pathogenic BRCA1 founder variant.", "Hereditary breast and ovarian cancer syndrome.",
    "Genetic counselling; discuss risk-reducing salpingo-oophorectomy and surveillance; test at-risk relatives.")

add("MOL09", "molecular", 22, "M", "Low back pain that improves with exercise; morning stiffness > 1 hour.",
    [A("HLA-B27", "Positive", "", "Negative")], "mild",
    "What is the most appropriate interpretation?",
    ["Supports but does not confirm axial spondyloarthritis; correlate with imaging and clinical criteria",
     "Confirms ankylosing spondylitis", "Excludes spondyloarthritis", "Indicates rheumatoid arthritis"],
    "A", "HLA-B27 positive with inflammatory back pain.", "Increases probability of axial spondyloarthritis; not diagnostic alone (present in ~6–8% of the general population).",
    "Rheumatology referral; MRI of sacroiliac joints.", trap=True, must_not="Must not state the result confirms diagnosis.")

add("MOL10", "molecular", 38, "F", "Unprovoked deep-vein thrombosis.",
    [A("Factor V Leiden (F5 c.1691G>A)", "Heterozygous", "", "Not detected")], "mild",
    "What is the most appropriate interpretation?",
    ["Heterozygous factor V Leiden modestly increases thrombosis risk; management of the current DVT follows standard anticoagulation and does not usually change because of this result",
     "Homozygous thrombophilia requiring lifelong anticoagulation", "No thrombophilia", "Result indicates bleeding disorder"],
    "A", "Heterozygous FVL after unprovoked DVT.", "Mild inherited thrombophilia.",
    "Standard anticoagulation; duration guided by the unprovoked nature of the event rather than by the FVL result.")

add("MOL11", "molecular", 60, "M", "Haemoglobin 19.5 g/dL, haematocrit 58%; erythropoietin low.",
    [A("JAK2 V617F (allele-specific PCR)", "Positive, allele burden 42%", "", "Not detected")], "critical",
    "What is the most appropriate interpretation?",
    ["Polycythaemia vera is very likely; haematology referral", "Secondary polycythaemia", "Normal finding", "Iron deficiency"],
    "A", "JAK2 V617F positive with erythrocytosis and low EPO.", "Meets major criteria for polycythaemia vera.",
    "Haematology referral; phlebotomy and cytoreduction as indicated.")

add("MOL12", "molecular", 66, "M", "Metastatic colorectal cancer; planning first-line therapy.",
    [A("KRAS/NRAS mutation (tumour tissue, NGS)", "KRAS G12D detected", "", "Wild type"),
     A("BRAF V600E", "Not detected", "", "Not detected")], "critical",
    "What is the most appropriate interpretation?",
    ["RAS-mutant tumour; anti-EGFR antibodies (cetuximab, panitumumab) are not indicated",
     "Anti-EGFR therapy is the preferred option", "Tumour is BRAF-mutant", "No molecular finding of relevance"],
    "A", "KRAS G12D mutation.", "RAS mutation predicts lack of benefit from anti-EGFR monoclonal antibodies.",
    "Chemotherapy with bevacizumab-based regimen rather than anti-EGFR therapy.", trap=True,
    must_not="Must not recommend cetuximab or panitumumab.")

add("MOL13", "molecular", 59, "M", "PSA 6.2 ng/mL; one prior negative biopsy; considering repeat biopsy.",
    [A("PCA3 score (urine, post-DRE)", "68", "", "<25 lower probability"), A("Total PSA", "6.2", "ng/mL", "<4.0")], "critical",
    "What is the most appropriate interpretation?",
    ["High PCA3 score increases the probability of prostate cancer on repeat biopsy; supports proceeding with MRI-targeted repeat biopsy",
     "PCA3 excludes prostate cancer", "PCA3 confirms cancer without biopsy", "Result is uninterpretable"],
    "A", "PCA3 68 after a negative biopsy with persistent PSA elevation.",
    "Elevated urinary PCA3 supports a higher likelihood of cancer on repeat biopsy.",
    "Multiparametric MRI and targeted repeat biopsy.")

add("MOL14", "molecular", 71, "M", "History of bladder cancer; surveillance cystoscopy equivocal.",
    [A("Urine FISH (chromosomes 3, 7, 17 and 9p21)", "Positive (polysomy in 12% of cells)", "", "Negative"),
     A("Urine cytology", "Atypical urothelial cells", "", "Negative")], "critical",
    "What is the most appropriate interpretation?",
    ["Positive FISH with atypical cytology indicates likely recurrence; biopsy of suspicious area and/or enhanced cystoscopy",
     "Negative surveillance; continue routine follow-up", "Findings indicate benign inflammation", "Result cannot be interpreted"],
    "A", "Positive UroVysion-type FISH with atypical cytology.", "High probability of urothelial carcinoma recurrence.",
    "Biopsy/resection of any suspicious lesion; consider blue-light cystoscopy and upper-tract imaging.")

add("MOL15", "molecular", 23, "M", "Urethral discharge; sexual contact two weeks ago.",
    [A("Chlamydia trachomatis NAAT (first-void urine)", "Detected", "", "Not detected"),
     A("Neisseria gonorrhoeae NAAT (first-void urine)", "Not detected", "", "Not detected")], "mild",
    "What is the most appropriate interpretation?",
    ["Chlamydial urethritis; treat (doxycycline) and notify partners", "No infection", "Gonococcal urethritis; give ceftriaxone",
     "Urinary tract infection; give nitrofurantoin"],
    "A", "Chlamydia detected, gonorrhoea not detected.", "Chlamydial urethritis.",
    "Doxycycline 100 mg twice daily for 7 days; partner notification; test for other STIs.")

add("MOL16", "molecular", 34, "F", "Cough for 6 weeks, night sweats; chest X-ray: right upper-lobe cavity.",
    [A("Mycobacterium tuberculosis PCR (sputum, Xpert MTB/RIF)", "MTB detected (medium); rifampicin resistance NOT detected", "", "Not detected")], "critical",
    "What is the most appropriate interpretation?",
    ["Pulmonary tuberculosis, rifampicin-susceptible; start standard four-drug therapy and notify public health",
     "Latent tuberculosis", "Non-tuberculous mycobacteria", "Result is falsely positive"],
    "A", "MTB detected without rifampicin resistance in a symptomatic patient with cavitary lesion.",
    "Active rifampicin-susceptible pulmonary tuberculosis.", "Start HRZE; culture and full susceptibility; public-health notification.")

add("MOL17", "molecular", 47, "M", "Asymptomatic; PCR done for travel clearance 3 weeks after mild COVID-19.",
    [A("SARS-CoV-2 RT-PCR (nasopharyngeal)", "Detected, Ct 36", "", "Not detected")], "normal",
    "What is the most appropriate interpretation?",
    ["Very low viral RNA level, most consistent with residual non-infectious RNA after recent infection; isolation is not indicated",
     "Highly infectious acute infection; isolate immediately", "Reinfection with a new variant", "Laboratory error"],
    "A", "Positive PCR with very high Ct value weeks after infection.", "Residual RNA shedding; unlikely to be infectious.",
    "No isolation needed; clinical correlation.", trap=True, must_not="Must not recommend isolation or treatment.")

add("MOL18", "molecular", 52, "M", "Planned percutaneous coronary intervention; clopidogrel to be prescribed.",
    [A("CYP2C19 genotype", "*2/*2 (poor metaboliser)", "", "*1/*1 normal metaboliser")], "critical",
    "What is the most appropriate interpretation?",
    ["Poor metaboliser; clopidogrel is likely ineffective — use an alternative P2Y12 inhibitor (prasugrel or ticagrelor) if not contraindicated",
     "Normal response to clopidogrel expected", "Increase clopidogrel dose", "Avoid all antiplatelet therapy"],
    "A", "CYP2C19 *2/*2.", "Poor metaboliser; reduced activation of clopidogrel.",
    "Prescribe prasugrel or ticagrelor per CPIC guidance.")

assert len(CASES) == 40, len(CASES)
assert len({c["case_id"] for c in CASES}) == 40
