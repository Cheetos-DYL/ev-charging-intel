"""Market + taxonomy matrix from PRD §2 and §3.

`query` = the PRD boolean (provenance + Serper). `bing_queries` = plain phrases —
Bing News RSS silently returns 0 for parenthesized booleans, so the news-search
channel runs one simple phrase query per entry.
"""
import os

# ---- LLM ----
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
GATEKEEPER_MODEL = os.environ.get("GATEKEEPER_MODEL", "deepseek-chat")
PROCESS_MODEL = os.environ.get("PROCESS_MODEL", "deepseek-chat")

# ---- Search APIs (optional; Bing News RSS works without keys) ----
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# ---- Supabase ----
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# ---- Telegram (Node 4) ----
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Direct publisher RSS feeds — real article URLs, no redirect decoding.
# Reused from ev-news-wiki's verified feed list.
# ponytail: coverage gap = markets without direct feeds rely on Bing phrases + SERPER_API_KEY;
# add verified local feeds per market when found.
DIRECT_FEEDS = [
    dict(region_group="KR", country_code="KR", language="ko",
         url="https://www.hankyung.com/feed/economy/auto", source_name="한국경제"),
    dict(region_group="TW", country_code="TW", language="zh-TW",
         url="https://technews.tw/feed/", source_name="TechNews"),
    dict(region_group="SG", country_code="SG", language="en",
         url="https://www.channelnewsasia.com/rss", source_name="CNA"),
    dict(region_group="AU_NZ", country_code="AU", language="en",
         url="https://thedriven.io/feed/", source_name="The Driven"),
    dict(region_group="AU_NZ", country_code="AU", language="en",
         url="https://evcentral.com.au/feed/", source_name="EV Central"),
    dict(region_group="AU_NZ", country_code="AU", language="en",
         url="https://www.reneweconomy.com.au/feed/", source_name="RenewEconomy"),
    dict(region_group="MENA", country_code="SA", language="en",
         url="https://www.arabnews.com/rss", source_name="Arab News"),
    dict(region_group="BR", country_code="BR", language="pt",
         url="https://canaltech.com.br/rss/", source_name="Canaltech"),
]

CATEGORY_TAGS = [
    "#CPO_Network",
    "#eMSP_Roaming",
    "#Policy_Subsidy",
    "#Hardware_Tech",
    "#Grid_Energy",
    "#OEM_Initiative",
    "#Partnership_MnA",
]

REGION_GROUPS = ["KR", "JP", "TW", "SG", "SEA", "AU_NZ", "MENA", "MX", "BR", "ZA"]

SEARCHES = [
    # KR
    dict(region_group="KR", country_code="KR", language="ko", hl="ko", gl="KR", ceid="KR:ko",
         query='("전기차 충전" OR "충전 인프라" OR "급속충전기") AND ("환경부" OR "구축" OR "CPO" OR "로밍" OR "보조금")',
         bing_queries=["전기차 충전", "충전 인프라", "급속충전기"]),
    # JP
    dict(region_group="JP", country_code="JP", language="ja", hl="ja", gl="JP", ceid="JP:ja",
         query='("EV充電" OR "急速充電器" OR "充電インフラ") AND ("設置" OR "補助金" OR "e-Mobility Power" OR "ENECHANGE")',
         bing_queries=["EV充電", "急速充電器", "充電インフラ"]),
    # TW
    dict(region_group="TW", country_code="TW", language="zh-TW", hl="zh-TW", gl="TW", ceid="TW:zh-TW",
         query='("電動車充電" OR "充電樁" OR "快充站") AND ("台電" OR "建置" OR "U-Power" OR "EVOASIS" OR "補助")',
         bing_queries=["電動車充電", "充電樁", "快充站"]),
    # SG (EN + ZH)
    dict(region_group="SG", country_code="SG", language="en", hl="en-SG", gl="SG", ceid="SG:en",
         query='("EV charging" OR "EV charger") AND ("Singapore" OR "LTA" OR "HDB" OR "EVe") AND ("tender" OR "deployment" OR "roaming" OR "TR25")',
         bing_queries=["EV charging Singapore", "EV charger Singapore"]),
    dict(region_group="SG", country_code="SG", language="zh-SG", hl="zh-SG", gl="SG", ceid="SG:zh-SG",
         query='("新加坡") AND ("电动车充电" OR "充电桩") AND ("陆交局" OR "建屋局")',
         bing_queries=["新加坡 充电桩", "新加坡 电动车充电"]),
    # SEA
    dict(region_group="SEA", country_code="TH", language="th", hl="th", gl="TH", ceid="TH:th",
         query='"สถานีชาร์จ EV" OR "หัวชาร์จรถยนต์ไฟฟ้า"',
         bing_queries=["สถานีชาร์จ EV", "จุดชาร์จรถไฟฟ้า"]),
    dict(region_group="SEA", country_code="ID", language="id", hl="id", gl="ID", ceid="ID:id",
         query='"SPKLU" OR "stasiun pengisian kendaraan listrik"',
         bing_queries=["SPKLU", "stasiun pengisian kendaraan listrik"]),
    dict(region_group="SEA", country_code="VN", language="vi", hl="vi", gl="VN", ceid="VN:vi",
         query='"trạm sạc xe điện" OR "V-Green"',
         bing_queries=["trạm sạc xe điện", "V-Green"]),
    dict(region_group="SEA", country_code="MY", language="en", hl="en-MY", gl="MY", ceid="MY:en",
         query='"EV charging" AND ("Malaysia" OR "TNB" OR "PLANMalaysia")',
         bing_queries=["EV charging Malaysia", "EV charger TNB"]),
    # AU_NZ
    dict(region_group="AU_NZ", country_code="AU", language="en", hl="en-AU", gl="AU", ceid="AU:en-AU",
         query='("EV charging" OR "fast charger") AND ("Australia" OR "New Zealand" OR "ARENA" OR "EECA" OR "NRMA" OR "Evie" OR "ChargeNet")',
         bing_queries=["EV charging Australia", "EV charger Australia", "fast charger Australia"]),
    dict(region_group="AU_NZ", country_code="NZ", language="en", hl="en-NZ", gl="NZ", ceid="NZ:en-NZ",
         query='("EV charging" OR "fast charger") AND ("Australia" OR "New Zealand" OR "ARENA" OR "EECA" OR "NRMA" OR "Evie" OR "ChargeNet")',
         bing_queries=["EV charging New Zealand", "EV charger NZ"]),
    # MENA
    dict(region_group="MENA", country_code="SA", language="ar", hl="ar", gl="SA", ceid="SA:ar",
         query='("شحن السيارات الكهربائية" OR "محطات شحن") AND ("السعودية" OR "الإمارات" OR "DEWA" OR "EVIQ")',
         bing_queries=["شحن السيارات الكهربائية", "محطات شحن كهربائية"]),
    dict(region_group="MENA", country_code="AE", language="en", hl="en", gl="AE", ceid="AE:en",
         query='"EV charging" AND ("UAE" OR "Saudi" OR "KSA" OR "DEWA" OR "TAQA" OR "EVIQ" OR "ADNOC")',
         bing_queries=["EV charging UAE", "EV charging Saudi"]),
    # MX
    dict(region_group="MX", country_code="MX", language="es", hl="es-419", gl="MX", ceid="MX:es-419",
         query='("infraestructura de carga" OR "electrolineras" OR "cargadores autos eléctricos") AND ("México" OR "CFE" OR "CRE")',
         bing_queries=["infraestructura de carga", "electrolineras"]),
    # BR
    dict(region_group="BR", country_code="BR", language="pt", hl="pt-BR", gl="BR", ceid="BR:pt-BR",
         query='("eletropostos" OR "infraestrutura de recarga" OR "carregadores carros eléctricos") AND ("Brasil" OR "ANEEL" OR "ABVE")',
         bing_queries=["eletropostos", "infraestrutura de recarga"]),
    # ZA
    dict(region_group="ZA", country_code="ZA", language="en", hl="en-ZA", gl="ZA", ceid="ZA:en-ZA",
         query='("EV charging" OR "electric vehicle charger") AND ("South Africa" OR "Eskom" OR "Zero Carbon Charge" OR "GridCars" OR "Rubicon")',
         bing_queries=["EV charging South Africa", "electric vehicle charger South Africa"]),
]
