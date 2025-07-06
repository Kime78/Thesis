import asyncio
import hashlib
import os
import time
from typing import Dict, List, Tuple

import aiofiles
import httpx
from rich.console import Console
from rich.table import Table

FILEREC_URL = "http://172.30.6.80:8080"
FILEDOWNLOADER_URL = "http://172.30.6.209:8000"
STATUS_ENDPOINT_URL = f"{FILEDOWNLOADER_URL}/status"

STORAGE_NODE_URLS = [
    "http://storage-node1:8000",
    "http://storage-node2:8000",
    "http://storage-node3:8000",
    "http://storage-node4:8000",
]

TEST_FILES_CONFIG = [
    {"size_kb": 10, "count": 40},
    {"size_kb": 1024, "count": 20},
    {"size_kb": 15 * 1024, "count": 5},
    {"size_kb": 100 * 1024, "count": 1},
]
CONCURRENT_REQUESTS = 4
BENCHMARK_DIR = "benchmark_files"

POLLING_TIMEOUT_SECONDS = 60
POLLING_INTERVAL_SECONDS = 0.5

console = Console()


async def create_test_file(filepath: str, size_kb: int):
    """Generates a file with random content."""
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(os.urandom(size_kb * 1024))


def get_file_hash(filepath: str) -> str:
    """Calculates the SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


async def get_system_status(client: httpx.AsyncClient, node_url: str) -> Dict:
    """Gets system status from a storage node."""
    try:
        response = await client.get(f"{node_url}/system-status", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        console.log(
            f"[bold red]Error contacting node {node_url}: {type(e).__name__} - {e.request.url}[/bold red]"
        )
        return {}


async def poll_for_status(client: httpx.AsyncClient, file_uuid: str) -> bool:
    """Polls the status endpoint until the file is ready or timeout occurs."""
    start_time = time.monotonic()
    while time.monotonic() - start_time < POLLING_TIMEOUT_SECONDS:
        try:
            response = await client.get(f"{STATUS_ENDPOINT_URL}/{file_uuid}")
            if response.status_code == 200:
                # console.log(f"[green]Ready:[/] Status OK for UUID {file_uuid}")
                return True
            elif response.status_code == 404:
                await asyncio.sleep(POLLING_INTERVAL_SECONDS)
                continue
            else:
                console.log(
                    f"[bold red]Error polling for UUID {file_uuid}: Status {response.status_code}[/bold red]"
                )
                return False
        except httpx.RequestError as e:
            console.log(
                f"[bold red]RequestError while polling for UUID {file_uuid}: {e}[/bold red]"
            )
            await asyncio.sleep(POLLING_INTERVAL_SECONDS)

    console.log(
        f"[bold yellow]Timeout:[/bold yellow] Polling for UUID {file_uuid} timed out after {POLLING_TIMEOUT_SECONDS} seconds."
    )
    return False


async def benchmark_upload(
    client: httpx.AsyncClient, file_configs: List[Tuple[str, int]]
) -> List[Dict]:
    """
    Runs the end-to-end upload benchmark.
    Returns a list of dictionaries with per-file results.
    """
    upload_results = []

    async def upload_and_poll(filepath: str, size_kb: int):
        filename = os.path.basename(filepath)
        start_time = time.monotonic()
        result = {
            "filename": filename,
            "size_kb": size_kb,
            "status": "Failed",
            "latency_s": None,
            "uuid": None,
            "error": "An unknown error occurred.",
        }

        try:
            with open(filepath, "rb") as f:
                response = await client.post(
                    f"{FILEREC_URL}/upload",
                    files={"uploaded_files": (filename, f, "application/octet-stream")},
                    timeout=120.0,
                )
                response.raise_for_status()

            response_data = response.json()
            if not (
                response_data
                and isinstance(response_data, list)
                and "file_uuid" in response_data[0]
            ):
                result["error"] = "Invalid response from upload endpoint."
                upload_results.append(result)
                return

            file_uuid = response_data[0]["file_uuid"]
            result["uuid"] = file_uuid

            is_ready = await poll_for_status(client, file_uuid)

            if is_ready:
                end_time = time.monotonic()
                result.update(
                    {
                        "status": "Success",
                        "latency_s": end_time - start_time,
                        "error": None,
                    }
                )
            else:
                result["error"] = (
                    f"Polling timed out or failed after {POLLING_TIMEOUT_SECONDS}s."
                )
        except httpx.HTTPStatusError as e:
            result["error"] = (
                f"HTTP Status {e.response.status_code} {e.response.reason_phrase}"
            )
        except httpx.RequestError as e:
            result["error"] = f"{type(e).__name__} on URL {e.request.url}"
        except Exception as e:
            result["error"] = f"An unexpected error occurred: {e}"

        upload_results.append(result)

    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def task_with_semaphore(path: str, size: int):
        async with semaphore:
            await upload_and_poll(path, size)

    tasks = [task_with_semaphore(path, size) for path, size in file_configs]
    await asyncio.gather(*tasks)
    return upload_results


async def benchmark_download(
    client: httpx.AsyncClient, uploaded_files: List[Dict], original_hashes: Dict
) -> List[Dict]:
    """
    Runs the download benchmark and verifies file integrity.
    Returns a list of dictionaries with per-file results.
    """
    download_results = []

    async def download_and_verify(file_info: Dict):
        file_uuid = file_info.get("uuid")
        original_filename = file_info.get("filename", "unknown_file")
        result = {
            "filename": original_filename,
            "uuid": file_uuid,
            "size_kb": file_info.get("size_kb"),  # Carry over size info
            "status": "Failed",
            "latency_s": None,
            "integrity": "Not Checked",
            "error": "An unknown error occurred",
        }

        if not file_uuid:
            result["error"] = "Missing file_uuid for download."
            download_results.append(result)
            return

        try:
            start_time = time.monotonic()
            response = await client.post(
                f"{FILEDOWNLOADER_URL}/download",
                json={"file_uuid": file_uuid},
                timeout=120.0,
            )
            response.raise_for_status()
            end_time = time.monotonic()

            downloaded_content = await response.aread()
            downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
            original_hash = original_hashes.get(original_filename)

            integrity_check = "Passed" if downloaded_hash == original_hash else "Failed"

            result.update(
                {
                    "status": "Success",
                    "latency_s": end_time - start_time,
                    "integrity": integrity_check,
                    "error": None,
                }
            )
        except httpx.HTTPStatusError as e:
            result["error"] = (
                f"HTTP Status {e.response.status_code} on URL {e.request.url}"
            )
        except httpx.RequestError as e:
            result["error"] = f"{type(e).__name__} on URL {e.request.url}"
        except Exception as e:
            result["error"] = f"An unexpected error occurred: {e}"

        download_results.append(result)

    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def task_with_semaphore(file_data: dict):
        async with semaphore:
            await download_and_verify(file_data)

    tasks = [task_with_semaphore(file_data) for file_data in uploaded_files]
    await asyncio.gather(*tasks)
    return download_results


def display_results(
    title: str,
    total_time: float,
    total_size_mb: float,
    latencies: List[float],
    success_count: int,
    total_count: int,
):
    """Displays benchmark summary results in a formatted table."""
    table = Table(
        title=title, style="black", show_header=True, header_style="bold black"
    )
    table.add_column("Metric", style="bold black")
    table.add_column("Value", justify="right")

    throughput = total_size_mb / total_time if total_time > 0 else 0
    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0

    table.add_row("Total time", f"{total_time:.2f} s")
    table.add_row("Total size", f"{total_size_mb:.2f} MB")
    table.add_row("Throughput", f"{throughput:.2f} MB/s")
    table.add_row("Successful operations", f"{success_count} / {total_count}")
    table.add_row("Success rate", f"{success_rate:.2f}%")

    if latencies:
        table.add_row(
            "Average latency", f"{sum(latencies) / len(latencies) * 1000:.2f} ms"
        )
        table.add_row("Min latency", f"{min(latencies) * 1000:.2f} ms")
        table.add_row("Max latency", f"{max(latencies) * 1000:.2f} ms")

    console.print(table)


def display_per_file_results(title: str, results: List[Dict]):
    """Displays per-file results in a detailed table."""
    if not results:
        return

    is_download = "integrity" in results[0]
    table = Table(
        title=title, style="default", show_header=True, header_style="bold black"
    )
    table.add_column("Filename", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    if is_download:
        table.add_column("Integrity", justify="center")
    table.add_column("Latency (ms)", justify="right")
    table.add_column("UUID", style="yellow", no_wrap=True)
    table.add_column("Error", style="red")

    for result in sorted(results, key=lambda r: r["size_kb"]):
        status_style = "green" if result["status"] == "Success" else "red"
        status = f"[{status_style}]{result['status']}[/]"
        latency_ms = (
            f"{result['latency_s'] * 1000:.2f}"
            if result["latency_s"] is not None
            else "N/A"
        )
        error_msg = result.get("error") or ""

        row_data = [result["filename"], status]
        if is_download:
            integrity = result.get("integrity", "N/A")
            integrity_style = (
                "green"
                if integrity == "Passed"
                else "red"
                if integrity == "Failed"
                else "yellow"
            )
            row_data.append(f"[{integrity_style}]{integrity}[/]")
        row_data.extend([latency_ms, result["uuid"] or "N/A", error_msg])
        table.add_row(*row_data)

    console.print(table)


def display_category_results(title: str, all_results: List[Dict], configs: List[Dict]):
    """Displays results aggregated by file size category."""
    table = Table(
        title=title, style="black", show_header=True, header_style="bold black"
    )
    table.add_column("Category (File Size)", justify="right")
    table.add_column("Successful", justify="center")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Latency (ms)", justify="right")
    table.add_column("Min Latency (ms)", justify="right")
    table.add_column("Max Latency (ms)", justify="right")

    for config in configs:
        size_kb = config["size_kb"]
        total_count = config["count"]

        category_results = [r for r in all_results if r.get("size_kb") == size_kb]
        successful = [r for r in category_results if r["status"] == "Success"]

        success_count = len(successful)
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0

        latencies_ms = [
            r["latency_s"] * 1000 for r in successful if r["latency_s"] is not None
        ]

        avg_latency = (
            f"{sum(latencies_ms) / len(latencies_ms):.2f}" if latencies_ms else "N/A"
        )
        min_latency = f"{min(latencies_ms):.2f}" if latencies_ms else "N/A"
        max_latency = f"{max(latencies_ms):.2f}" if latencies_ms else "N/A"

        size_str = f"{size_kb} KB" if size_kb < 1024 else f"{size_kb / 1024} MB"

        table.add_row(
            size_str,
            f"{success_count}/{total_count}",
            f"{success_rate:.2f}%",
            avg_latency,
            min_latency,
            max_latency,
        )
    console.print(table)


def display_system_status(title: str, status: Dict):
    """Displays system status."""
    if not status:
        return
    table = Table(title=title, style="green")
    table.add_column("Resource", style="bold blue")
    table.add_column("Usage (%)", justify="right")
    table.add_column("Details")
    table.add_row("CPU", f"{status['cpu']['usage_percent']:.2f}%", "")
    table.add_row(
        "RAM",
        f"{status['ram']['usage_percent']:.2f}%",
        f"Used: {status['ram']['used'] / (1024**3):.2f} / {status['ram']['total'] / (1024**3):.2f} GB",
    )
    table.add_row(
        "Disk",
        f"{status['disk']['usage_percent']:.2f}%",
        f"Free: {status['disk']['free'] / (1024**3):.2f} GB",
    )
    console.print(table)


async def main():
    """Orchestrates the entire benchmarking process."""
    console.rule("[bold]Initiating Distributed File System Benchmark[/bold]")
    console.log(f"Creating test files in '{BENCHMARK_DIR}' directory...")
    os.makedirs(BENCHMARK_DIR, exist_ok=True)

    file_configs = []
    original_hashes = {}
    total_file_count = sum(c["count"] for c in TEST_FILES_CONFIG)
    total_size_bytes = 0

    for config in TEST_FILES_CONFIG:
        for i in range(config["count"]):
            filename = f"test_{config['size_kb']}kb_{i + 1}.bin"
            filepath = os.path.join(BENCHMARK_DIR, filename)
            await create_test_file(filepath, config["size_kb"])
            file_configs.append((filepath, config["size_kb"]))
            original_hashes[filename] = get_file_hash(filepath)
            total_size_bytes += config["size_kb"] * 1024

    total_size_mb = total_size_bytes / (1024 * 1024)
    console.log(
        f"{len(file_configs)} test files created, total size {total_size_mb:.2f} MB."
    )

    async with httpx.AsyncClient() as client:
        console.rule("[bold]System Status Before Test[/bold]")
        initial_statuses = await asyncio.gather(
            *(get_system_status(client, url) for url in STORAGE_NODE_URLS)
        )
        for i, status in enumerate(initial_statuses):
            display_system_status(f"Storage Node {i + 1} - Initial State", status)

        console.rule("[bold]End-to-End Upload & Processing Benchmark[/bold]")
        start_upload_time = time.monotonic()
        upload_results = await benchmark_upload(client, file_configs)
        end_upload_time = time.monotonic()

        successful_uploads = [r for r in upload_results if r["status"] == "Success"]

        display_category_results(
            "Upload & Processing Results by Category", upload_results, TEST_FILES_CONFIG
        )
        display_per_file_results("Upload", upload_results)
        display_results(
            "Upload",
            total_time=end_upload_time - start_upload_time,
            total_size_mb=sum(r["size_kb"] for r in successful_uploads) / 1024,
            latencies=[r["latency_s"] for r in successful_uploads],
            success_count=len(successful_uploads),
            total_count=total_file_count,
        )

        if not successful_uploads:
            console.log(
                "[bold red]No files were successfully processed. Skipping download test.[/bold red]"
            )
            return

        await asyncio.sleep(5)

        console.rule("[bold]Download Benchmark[/bold]")
        start_download_time = time.monotonic()
        download_results = await benchmark_download(
            client, successful_uploads, original_hashes
        )
        end_download_time = time.monotonic()

        successful_downloads = [r for r in download_results if r["status"] == "Success"]
        mismatched_hashes = len(
            [r for r in successful_downloads if r["integrity"] == "Failed"]
        )

        display_category_results(
            "Download Results by Category", download_results, TEST_FILES_CONFIG
        )
        display_per_file_results("Download", download_results)
        display_results(
            "Download",
            total_time=end_download_time - start_download_time,
            total_size_mb=sum(r["size_kb"] for r in successful_downloads) / 1024,
            latencies=[r["latency_s"] for r in successful_downloads],
            success_count=len(successful_downloads),
            total_count=len(successful_uploads),
        )

        if mismatched_hashes > 0:
            console.print(
                f"[bold red]Warning: {mismatched_hashes} downloaded files had incorrect hashes![/bold red]"
            )
        elif successful_downloads and not mismatched_hashes:
            console.print(
                "[bold green]File integrity check passed for all downloaded files![/bold green]"
            )

        console.rule("[bold]System Status After Test[/bold]")
        final_statuses = await asyncio.gather(
            *(get_system_status(client, url) for url in STORAGE_NODE_URLS)
        )
        for i, status in enumerate(final_statuses):
            display_system_status(f"Storage Node {i + 1} - Final State", status)

    console.log(
        f"Test files in '{BENCHMARK_DIR}' have been kept for manual inspection."
    )


if __name__ == "__main__":
    asyncio.run(main())
