from datetime import datetime
import os
import requests
import time
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress

SLEEP_TIME_SECS_BETWEEN_REQUESTS = 5
console = Console()


def splash_screen():
    console.clear()
    atoto_logo = """
    ___   ______ ____  ______ ____
   /   | /_  __// __ \/_  __// __ \\
  / /| |  / /  / / / / / /  / / / /
 / ___ | / /  / /_/ / / /  / /_/ /
/_/  |_|/_/   \____/ /_/   \____/

"""
    console.print("[bold magenta]" + atoto_logo + "[/bold magenta]")
    console.print("[bold yellow]Firmware Downloader v1.01[/bold yellow]")
    console.print("[cyan]by raleighlittles and CatKinKitKat[/cyan]")
    time.sleep(2)
    console.clear()


def get_url(endpoint: str, **params) -> str:
    base_url = "https://resources.myatoto.com/atoto-product-ibook/ibMobile/"
    return f"{base_url}{endpoint}?{'&'.join(f'{k}={v}' for k, v in params.items())}"


def download_file(url: str, path: str) -> None:
    response = requests.get(url, stream=True)
    if not response.ok:
        console.print(
            f"Failed to download: HTTP {response.status_code}", style="bold red"
        )
        return
    total_length = int(response.headers.get("content-length"))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as file, Progress() as progress:
        task = progress.add_task("Downloading...", total=total_length)
        for chunk in response.iter_content(chunk_size=4096):
            file.write(chunk)
            progress.update(task, advance=len(chunk))
    console.print(f"Downloaded to {path}", style="bold green")


def select_firmware(firmwares: list) -> str:
    for i, fw in enumerate(firmwares, start=1):
        console.print(f"{i}. {fw}")
    choice = IntPrompt.ask("Select firmware to download (number)", default=1) - 1
    if 0 <= choice < len(firmwares):
        return firmwares[choice]
    console.print("Invalid selection.", style="bold red")
    return None


def main() -> None:
    splash_screen()
    product_model = Prompt.ask("Enter product model", default="F7G2A7WE")
    mcu_version = Prompt.ask("Enter MCU version (leave blank if unsure)", default="")

    firmware_page_url = get_url(
        "getIbookList",
        skuModel=product_model,
        mcuVersion=mcu_version,
        langType=1,
        iBookType=2,
    )
    resp = requests.get(firmware_page_url).json()
    firmware_urls = [resp["data"]["softwareVo"]["socVo"]["socUrl"]]

    selected_url = select_firmware(firmware_urls)
    if not selected_url:
        console.print(
            "Download canceled due to invalid firmware selection.", style="bold red"
        )
        return

    filename = selected_url.split("/")[-1]
    download_path = os.path.join("firmware_downloads", product_model, filename)
    download_file(selected_url, download_path)


if __name__ == "__main__":
    main()
