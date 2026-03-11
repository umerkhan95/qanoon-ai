"""Shared constants for the Sindh High Court crawler pipeline."""

BASE_URL = "https://caselaw.shc.gov.pk/caselaw"

# Public report page listing all judges with judgment counts
JUDGES_REPORT_URL = f"{BASE_URL}/public/rpt-afr"

# URL template for individual judge's judgments. Params: judge_id, filter.
# filter = "-1" for all, "AFR/AFR" for approved-for-reporting only.
JUDGE_JUDGMENTS_URL_TEMPLATE = (
    f"{BASE_URL}/public/reported-judgements-detail-all/{{judge_id}}/{{filter}}"
)

# PDF download URL pattern (relative to BASE_URL)
PDF_DOWNLOAD_URL = f"{BASE_URL}/public/download-file.php"

# Court code used in Qdrant point IDs
COURT_CODE = "SHC"

# Known judge IDs from recon (as of March 2026)
# Maps judge_id -> judge name for reference
JUDGE_IDS = {
    844: "Zafar Ahmed Rajput",
    883: "Muhammad Iqbal Kalhoro",
    965: "Mahmood A. Khan",
    966: "Muhammad Faisal Kamal Alam",
    1023: "Muhammad Saleem Jessar",
    1041: "Arshad Hussain Khan",
    1061: "Adnan-ul-Karim Memon",
    1101: "Khadim Hussain Tunio",
    1102: "Yousuf Ali Sayeed",
    1121: "Omar Sial",
    1162: "Shamsuddin Abbasi",
    1181: "Agha Faisal",
    1182: "Amjad Ali Sahito",
    1201: "Adnan Iqbal Chaudhry",
    1242: "Abdul Mobeen Lakho",
    1243: "Zulfiqar Ali Sangi",
    1261: "Amjad Ali Bohio",
    1263: "Sana Akram Minhas",
    1264: "Jawad Akbar Sarwana",
    1266: "Muhammad Abdur Rahman",
    1267: "Arbab Ali Hakro",
    1301: "Miran Muhammad Shah",
    1302: "Tasneem Sultana",
    1303: "Riazat Ali Sahar",
    1304: "Muhammad Hasan (Akber)",
    1305: "Khalid Hussain Shahani",
    1306: "Abdul Hamid Bhurgri",
    1307: "Syed Fiaz Ul Hassan Shah",
    1308: "Jan Ali Junejo",
    1309: "Nisar Ahmed Bhanbhro",
    1310: "Ali Haider 'Ada'",
    1311: "Muhammad Osman Ali Hadi",
    1312: "Muhammad Jaffer Raza",
}
