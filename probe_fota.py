import requests
import json
import urllib3
from rich import print

# Disable SSL warnings for this probe
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://fota.redstone.net.cn:7100/service/request"

# Payload from user screenshot
payload = {
    "version": "A1.0",
    "session": "FUMO-REQ",
    "devid": "SN:5319f700",  # Sample SN
    "man": "ATOTO",
    "mod": "qcm6125_T10",    # X10 model
    "swv": "20250318.213333", # Base version
    "carrier": {
        "appid": "ilppa7c9qlze3znkzaaxdqpa",
        "channel": "myatoto"
    }
}

print(f"[bold cyan]Probing Redstone FOTA:[/] {URL}")
try:
    # Mimic android User-Agent just in case
    headers = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; X10G2A7E Build/QUokka)"}
    
    r = requests.post(URL, json=payload, headers=headers, timeout=15, verify=False)
    print(f"\n[bold]Status:[/] {r.status_code}")
    
    try:
        data = r.json()
        print(f"[bold green]JSON Response:[/]")
        print(json.dumps(data, indent=2))
        
        # Check download URL
        if "romUrl" in str(data):
            print("\n[bold yellow]Found Firmware URL![/]")
    except:
        print(f"[red]Not JSON:[/]\n{r.str}")

except Exception as e:
    print(f"[bold red]Error:[/] {e}")
