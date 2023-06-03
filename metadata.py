#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python311 python311.pkgs.aiohttp

import asyncio
import base64
import hashlib
import json
import logging
import os
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from itertools import product
from typing import Any

import aiohttp

MIN_RELEASE_VERSION = 16
MIN_TOOLS_VERSION = 12


@dataclass
class System:
    name: str
    download_name: str


@dataclass
class Devkit:
    name: str

    def download_file_for(self, version: str, system: System) -> str:
        return f"{self.name}-devkit-{version}-{system.download_name}.tar.xz"

    def download_url_for(self, version: str, system: System) -> str:
        file = self.download_file_for(version, system)
        return f"https://github.com/frida/frida/releases/download/{version}/{file}"


SYSTEMS = [
    System("aarch64-darwin", "macos-arm64"),
    System("aarch64-linux", "linux-arm64"),
    System("x86_64-darwin", "macos-x86_64"),
    System("x86_64-linux", "linux-x86_64"),
]

DEVKITS = [
    Devkit("frida-core"),
    Devkit("frida-gum"),
    Devkit("frida-gumjs"),
]

logging.basicConfig(level=logging.INFO)


class Fetcher:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        metadata: dict[str, Any],
    ) -> None:
        self.session = session
        self.metadata = metadata
        self.limiter = asyncio.BoundedSemaphore(os.cpu_count() or 1)

    async def __call__(self) -> None:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                self.fetch_frida_devkit(tg.create_task(self.fetch_frida_python()))
            )
            tg.create_task(self.fetch_frida_tools())

    async def fetch_frida_python(self) -> None:
        logging.info("fetching frida-python")
        latest, releases = await self.fetch_pypi_project("frida")
        for version, (url, sri) in releases:
            self.metadata["releases"][version]["frida-python"] = {
                "url": url,
                "sha256": sri,
            }
        self.metadata["latest-release"] = latest
        self._filter_version(self.metadata["releases"], MIN_RELEASE_VERSION)

    async def fetch_frida_tools(self) -> None:
        logging.info("fetching frida-tools")
        latest, tools = await self.fetch_pypi_project("frida-tools")
        for version, (url, sri) in tools:
            self.metadata["tools"][version] = {
                "url": url,
                "sha256": sri,
            }
        self.metadata["latest-tools"] = latest
        self._filter_version(self.metadata["tools"], MIN_TOOLS_VERSION)

    async def fetch_pypi_project(
        self,
        name: str,
    ) -> tuple[str, list[tuple[str, tuple[str, str]]]]:
        async with self.session.get(f"https://pypi.org/pypi/{name}/json") as resp:
            resp.raise_for_status()
            result = await resp.json()
        releases: list[tuple[str, tuple[str, str]]] = []
        for version, files in reversed(result["releases"].items()):
            sdist = self._get_sdist(files)
            if sdist is not None:
                sri = self._hex_encoded_sha256_to_sri(sdist["digests"]["sha256"])
                releases.append((version, (sdist["url"], sri)))
        return result["info"]["version"], releases

    async def fetch_frida_devkit(
        self, fetch_frida_python_task: asyncio.Task[None]
    ) -> None:
        await fetch_frida_python_task
        async with asyncio.TaskGroup() as tg:
            releases = self.metadata["releases"]
            for (version, system, devkit) in product(releases.keys(), SYSTEMS, DEVKITS):
                per_system = releases[version].setdefault("per-system", {})
                sources = per_system.setdefault(system.name, {})
                source = sources.setdefault(devkit.name, {})
                tg.create_task(
                    self._fetch_frida_devkit_for(source, version, system, devkit)
                )

    async def _fetch_frida_devkit_for(
        self,
        source: dict[str, str],
        version: str,
        system: System,
        devkit: Devkit,
    ) -> None:
        if source.get("sha256", "") != "":
            return
        source["url"] = url = devkit.download_url_for(version, system)
        async with self.limiter:
            logging.info(f"fetching {devkit.name}-{version} for {system.name}")
            async with self.session.get(url) as resp:
                resp.raise_for_status()
                sha256 = hashlib.sha256(await resp.read()).digest()
                source["sha256"] = self._sha256_to_sri(sha256)

    def _sha256_to_sri(self, sha256: bytes) -> str:
        return "sha256-%s" % base64.b64encode(sha256).decode("utf-8")

    def _hex_encoded_sha256_to_sri(self, sha256: str) -> str:
        return self._sha256_to_sri(bytes.fromhex(sha256))

    def _get_sdist(self, files: list[dict[str, str]]) -> dict[str, Any] | None:
        sdist = filter(lambda file: file.get("packagetype", None) == "sdist", files)
        return next(sdist, None)

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        return tuple(map(int, version.split(".")))

    def _filter_version(
        self,
        d: dict[str, Any],
        min_major_version: int,
    ):
        for version in list(d.keys()):
            (major, _, _) = self._parse_version(version)
            if major < min_major_version:
                del d[version]


async def main(metadata: dict[str, Any]) -> None:
    async with aiohttp.ClientSession() as session:
        await Fetcher(session, metadata)()


if __name__ == "__main__":
    metadata: dict[str, Any] = {
        "latest-release": "",
        "latest-tools": "",
        "releases": {},
        "tools": {},
    }

    with suppress(FileNotFoundError):
        with open("metadata.json", "r") as f:
            metadata.update(json.load(f))

    metadata["releases"] = defaultdict(dict, metadata["releases"])
    metadata["tools"] = defaultdict(dict, metadata["tools"])

    try:
        asyncio.run(main(metadata))
    finally:
        with open("metadata.json", "w+") as f:
            json.dump(metadata, f, indent=2)
            f.write("\n")
