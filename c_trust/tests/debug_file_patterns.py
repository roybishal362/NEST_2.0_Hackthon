
import glob
import re
from enum import Enum
from pathlib import Path

# Mock FileType enum for standalone testing
class FileType(str, Enum):
    EDC_METRICS = "edc_metrics"
    VISIT_PROJECTION = "visit_projection"
    MISSING_PAGES = "missing_pages"
    MISSING_LAB = "missing_lab"
    SAE_DM = "sae_dm"
    SAE_SAFETY = "sae_safety"
    INACTIVATED = "inactivated"
    EDRR = "edrr"
    MEDDRA = "meddra"
    WHODD = "whodd"

# Failing filenames from user logs
FAILING_FILENAMES = [
    "SAE Dashboard_updated.xlsx",
    "Study 2_GlobalCodingReport_Medra_updated.xlsx",
    "Study 2_GlobalCodingReport_WHOdra_updated.xlsx",
    "Study 4_Missing_page_report_13Nov2025_updated.xlsx",
    "Study 7_GlobalCodingReport_whoDrug_updated.xlsx",
    "GlobalCodingReport _WHODrug_updated.xlsx",
    "Study 11_MedDRA_updated.xlsx",
    "Study 11_WHODD_updated.xlsx",
    "Study 13_MedDRA_14Nov25_updated.xlsx",
    "Study 13_WHODD_14Nov25_updated.xlsx",
    "GlobalCodingReport_MedRA CodingReport_Nov2025_updated.xlsx",
    "GlobalCodingReport_WHODrug Coding Report_Nov 2025_updated.xlsx",
    "eSAE_updated_30-Oct-2025_updated.xlsx",
    "Missing Page Report_updated.xlsx",
    "Study 19_MedDRA_updated.xlsx",
    "Study 19_WHODD_updated.xlsx",
    "GlobalCodingReport WHODrug_updated.xlsx",
    "Global Coding Report_Medra 4_updated.xlsx",
    "Global Coding Report_WHODD 4_updated.xlsx",
    "Missing LNR_Standard Metrics Input File template_updated.xlsx",
    "Study 22_Missing visit_updated.xlsx"
]

# Current patterns from config
CURRENT_PATTERNS = {
    FileType.EDC_METRICS: "*CPID_EDC*Metrics*.xlsx",
    FileType.VISIT_PROJECTION: "*Visit*Projection*Tracker*.xlsx",
    FileType.MISSING_PAGES: "*Missing*Pages*.xlsx",
    FileType.MISSING_LAB: "*Missing*Lab*.xlsx",
    FileType.SAE_DM: "*eSAE*Dashboard*DM*.xlsx",
    FileType.SAE_SAFETY: "*SAE*Dashboard*Standard*Metrics*.xlsx",
    FileType.INACTIVATED: "*Inactivated*.xlsx",
    FileType.EDRR: "*Compiled*EDRR*.xlsx",
    FileType.MEDDRA: "*GlobalCodingReport*MedDRA*.xlsx",
    FileType.WHODD: "*GlobalCodingReport*WHODD*.xlsx"
}

# New PROPOSED patterns (testing these)
PROPOSED_PATTERNS = {
   # Matching "CPID_EDC*Metrics", "Standard Metrics Input File"
   FileType.EDC_METRICS: ["*CPID_EDC*Metrics*.xlsx", "*Standard*Metrics*.xlsx"],

   # Matching "Visit Projection", "Missing visit"
   FileType.VISIT_PROJECTION: ["*Visit*Projection*.xlsx", "*Missing*visit*.xlsx"],

   # Matching "Missing Pages", "Missing Page Report", "Missing_page_report"
   FileType.MISSING_PAGES: ["*Missing*Page*.xlsx"],

   # Matching "Missing Lab", "Missing LNR"
   FileType.MISSING_LAB: ["*Missing*Lab*.xlsx", "*Missing*LNR*.xlsx"],

   # Matching "eSAE", "SAE Dashboard"
   FileType.SAE_DM: ["*eSAE*.xlsx", "*SAE*Dashboard*.xlsx"],

   # Matching the specific SAE Safety file if it exists, otherwise SAE_DM might catch it.
   # But based on user logs, "SAE Dashboard_updated.xlsx" is appearing.
   # We need to distinguish DM vs Safety if possible, or mapping them to one.
   # If user logs show "SAE Dashboard_updated.xlsx", and we have SAE_DM and SAE_SAFETY.
   # Let's map general SAE to SAE_SAFETY if not eSAE?
   FileType.SAE_SAFETY: ["*SAE*Safety*.xlsx"], # Keep specific or merge?

   # Matching "Inactivated"
   FileType.INACTIVATED: ["*Inactivated*.xlsx"],

   # Matching "EDRR", "Compiled EDRR"
   FileType.EDRR: ["*EDRR*.xlsx"],

   # Matching "MedDRA", "Medra", "MedRA"
   FileType.MEDDRA: ["*MedDRA*.xlsx", "*Medra*.xlsx", "*MedRA*.xlsx"],

   # Matching "WHODD", "WHOdra", "whoDrug", "WHODrug"
   FileType.WHODD: ["*WHODD*.xlsx", "*WHOdra*.xlsx", "*whoDrug*.xlsx", "*WHODrug*.xlsx"]
}

def glob_to_regex(pattern: str) -> str:
    regex = re.escape(pattern).replace('\\*', '.*').replace('\\?', '.')
    return f"^{regex}$"

def test_patterns(patterns_dict, description):
    print(f"\n--- Testing {description} ---")
    compiled_patterns = []
    for ftype, pat_input in patterns_dict.items():
        if isinstance(pat_input, list):
            for p in pat_input:
                compiled_patterns.append((ftype, re.compile(glob_to_regex(p), re.IGNORECASE)))
        else:
            compiled_patterns.append((ftype, re.compile(glob_to_regex(pat_input), re.IGNORECASE)))

    passed_count = 0
    failed_files = []

    for filename in FAILING_FILENAMES:
        detected = None
        for file_type, pattern in compiled_patterns:
            if pattern.match(filename):
                detected = file_type
                break
        
        if detected:
            passed_count += 1
            # print(f"✅ {filename} -> {detected.value}")
        else:
            failed_files.append(filename)
            # print(f"❌ {filename}")

    print(f"Passed: {passed_count}/{len(FAILING_FILENAMES)}")
    if failed_files:
        print("Failed files:")
        for f in failed_files:
            print(f"  - {f}")
    return passed_count == len(FAILING_FILENAMES)

if __name__ == "__main__":
    test_patterns(CURRENT_PATTERNS, "Current Patterns (Expect Failures)")
    
    # We will refine proposed patterns based on this script's failure output manually if needed, 
    # but let's try the proposed ones I wrote above which look wider.
    test_patterns(PROPOSED_PATTERNS, "Proposed Patterns")
