import requests
from requests.adapters import HTTPAdapter, Retry

UA   = "ATOTO-Firmware-CLI/3.2"

def make_session() -> requests.Session:
    retries = Retry(
        total=2, backoff_factor=0.3,
        status_forcelist=(429,500,502,503,504),
        allowed_methods=frozenset(["GET","HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    s = requests.Session()
    s.mount("http://", adapter); s.mount("https://", adapter)
    s.headers.update({"User-Agent": UA})
    return s

SESSION = make_session()
