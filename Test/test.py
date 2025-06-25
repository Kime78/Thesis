import asyncio
import hashlib
import os
import time
from typing import Dict, List, Tuple

import aiofiles
import httpx
from rich.console import Console
from rich.table import Table

FILEREC_URL = "http://172.30.6.13:8080"
FILEDOWNLOADER_URL = "http://172.30.6.237:8000"
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
                console.log(f"[green]Ready:[/] Status OK for UUID {file_uuid}")
                return True
            elif response.status_code == 404:
                # This is expected while the file is processing
                await asyncio.sleep(POLLING_INTERVAL_SECONDS)
                continue
            else:
                # Handle other unexpected status codes
                console.log(
                    f"[bold red]Error polling for UUID {file_uuid}: Status {response.status_code}[/bold red]"
                )
                return False
        except httpx.RequestError as e:
            console.log(
                f"[bold red]RequestError while polling for UUID {file_uuid}: {e}[/bold red]"
            )
            # Wait before retrying on connection errors
            await asyncio.sleep(POLLING_INTERVAL_SECONDS)

    console.log(
        f"[bold yellow]Timeout:[/bold yellow] Polling for UUID {file_uuid} timed out after {POLLING_TIMEOUT_SECONDS} seconds."
    )
    return False


async def benchmark_upload(
    client: httpx.AsyncClient, file_paths: List[str]
) -> Tuple[List[Dict], List[float]]:
    """
    Runs the end-to-end upload benchmark. The timer stops only after the
    status endpoint confirms the file is processed and ready.
    """
    latencies = []
    upload_results = []

    async def upload_and_poll(filepath: str):
        filename = os.path.basename(filepath)
        start_time = time.monotonic()  # Start timer before anything happens

        try:
            # 1. Initial upload request
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
                console.log(
                    f"[bold red]Upload failed for {filename}: Invalid response from upload endpoint.[/bold red]"
                )
                return

            file_uuid = response_data[0]["file_uuid"]
            console.log(
                f"[cyan]Upload sent for {filename} (UUID: {file_uuid}). Now polling for ready status...[/cyan]"
            )

            # 2. Poll for status
            is_ready = await poll_for_status(client, file_uuid)

            if is_ready:
                end_time = time.monotonic()  # Stop timer only after file is ready
                latencies.append(end_time - start_time)
                upload_results.append(response_data[0])
            else:
                # Polling failed (e.g., timed out)
                console.log(
                    f"[bold red]Processing failed for {filename} (UUID: {file_uuid}).[/bold red]"
                )

        except httpx.HTTPStatusError as e:
            console.log(
                f"[bold red]Upload failed for {filename}: {e.response.status_code} {e.response.reason_phrase}[/bold red]"
            )
        except httpx.RequestError as e:
            console.log(
                f"[bold red]Upload failed for {filename}: {type(e).__name__} - {e.request.url}[/bold red]"
            )
        except Exception as e:
            console.log(
                f"[bold red]An unexpected error occurred during upload of {filename}: {e}[/bold red]"
            )

    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def task_with_semaphore(path: str):
        async with semaphore:
            await upload_and_poll(path)

    tasks = [task_with_semaphore(path) for path in file_paths]
    await asyncio.gather(*tasks)
    return upload_results, latencies


async def benchmark_download(
    client: httpx.AsyncClient, uploaded_files: List[Dict], original_hashes: Dict
) -> Tuple[List[float], int]:
    """Runs the download benchmark and verifies file integrity."""
    latencies = []
    mismatched_hashes = 0

    download_dir = os.path.join(BENCHMARK_DIR, "downloads")
    os.makedirs(download_dir, exist_ok=True)

    async def download_and_verify(file_info: Dict):
        nonlocal mismatched_hashes
        file_uuid = file_info.get("file_uuid")
        original_filename = file_info.get("filename", "unknown_file")
        if not file_uuid:
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

            latencies.append(end_time - start_time)

            downloaded_content = await response.aread()
            downloaded_hash = hashlib.sha256(downloaded_content).hexdigest()
            original_hash = original_hashes.get(original_filename)

            if downloaded_hash != original_hash:
                mismatched_hashes += 1
                console.log(f"[red]Hash mismatch[/red] for file {original_filename}")

        except httpx.HTTPStatusError as e:
            console.log(
                f"[bold red]Download failed for UUID {file_uuid}: {e.response.status_code} {e.response.reason_phrase} on URL {e.request.url}[/bold red]"
            )
        except httpx.RequestError as e:
            console.log(
                f"[bold red]Download failed for UUID {file_uuid}: {type(e).__name__} - {e.request.url}[/bold red]"
            )
        except Exception as e:
            console.log(
                f"[bold red]An unexpected error occurred during download of {file_uuid}: {e}[/bold red]"
            )

    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def task_with_semaphore(file_data: dict):
        async with semaphore:
            await download_and_verify(file_data)

    tasks = [task_with_semaphore(file_data) for file_data in uploaded_files]
    await asyncio.gather(*tasks)
    return latencies, mismatched_hashes


def display_results(
    title: str,
    total_time: float,
    total_size_mb: float,
    latencies: List[float],
    success_count: int,
    total_count: int,
):
    """Displays benchmark results in a formatted table."""
    table = Table(title=title, style="cyan")
    table.add_column("Metric", style="bold magenta")
    table.add_column("Value")

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
    file_paths = []
    total_size_bytes = 0
    original_hashes = {}

    for config in TEST_FILES_CONFIG:
        for i in range(config["count"]):
            filename = f"test_{config['size_kb']}kb_{i + 1}.bin"
            filepath = os.path.join(BENCHMARK_DIR, filename)
            await create_test_file(filepath, config["size_kb"])
            file_paths.append(filepath)
            total_size_bytes += config["size_kb"] * 1024
            original_hashes[filename] = get_file_hash(filepath)

    total_size_mb = total_size_bytes / (1024 * 1024)
    console.log(
        f"{len(file_paths)} test files created, total size {total_size_mb:.2f} MB."
    )

    async with httpx.AsyncClient() as client:
        console.rule("[bold]System Status Before Test[/bold]")
        initial_statuses = await asyncio.gather(
            *(get_system_status(client, url) for url in STORAGE_NODE_URLS)
        )
        for i, status in enumerate(initial_statuses):
            display_system_status(f"Storage Node {i + 1} - Initial State", status)

        # MODIFICATION: Changed title to reflect what is being measured
        console.rule("[bold]End-to-End Upload & Processing Benchmark[/bold]")
        start_upload_time = time.monotonic()
        uploaded_files, upload_latencies = await benchmark_upload(client, file_paths)
        end_upload_time = time.monotonic()

        # MODIFICATION: Changed title
        display_results(
            "Upload & Processing Results",
            total_time=end_upload_time - start_upload_time,
            total_size_mb=total_size_mb,
            latencies=upload_latencies,
            success_count=len(upload_latencies),
            total_count=len(file_paths),
        )

        if not uploaded_files:
            console.log(
                "[bold red]No files were successfully processed. Skipping download test.[/bold red]"
            )
            return

        await asyncio.sleep(5)

        console.rule("[bold]Download Benchmark[/bold]")
        start_download_time = time.monotonic()
        download_latencies, mismatched_hashes = await benchmark_download(
            client, uploaded_files, original_hashes
        )
        end_download_time = time.monotonic()

        display_results(
            "Download Results",
            total_time=end_download_time - start_download_time,
            total_size_mb=total_size_mb if len(download_latencies) > 0 else 0,
            latencies=download_latencies,
            success_count=len(download_latencies),
            total_count=len(uploaded_files),
        )
        if mismatched_hashes > 0:
            console.print(
                f"[bold red]Warning: {mismatched_hashes} downloaded files had incorrect hashes![/bold red]"
            )
        elif len(download_latencies) > 0 and len(download_latencies) == len(
            uploaded_files
        ):
            console.print(
                "[bold green]File integrity check passed successfully![/bold green]"
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
