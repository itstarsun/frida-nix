#! /usr/bin/env python3

import asyncio
import base64
import hashlib
import json
import logging
import os
from collections import defaultdict
from contextlib import suppress
from itertools import product
from typing import Any

import aiohttp

MIN_RELEASE_VERSION = 16
MIN_TOOLS_VERSION = 12

SYSTEMS = [
    "aarch64-darwin",
    "aarch64-linux",
    "x86_64-darwin",
    "x86_64-linux",
]

DEVKITS = [
    "frida-core",
    "frida-gum",
    "frida-gumjs",
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
            for (version, system, name) in product(releases.keys(), SYSTEMS, DEVKITS):
                per_system = releases[version].setdefault("per-system", {})
                sources = per_system.setdefault(system, {})
                source = sources.setdefault(name, {})
                tg.create_task(
                    self._fetch_frida_devkit_for(source, version, system, name)
                )

    async def _fetch_frida_devkit_for(
        self,
        source: dict[str, str],
        version: str,
        system: str,
        name: str,
    ) -> None:
        if source.get("sha256", "") != "":
            return
        async with self.limiter:
            logging.info(f"fetching {name}-{version} for {system}")
            source["url"] = self._generate_source_url(version, system, name)
            async with self.session.get(source["url"]) as resp:
                resp.raise_for_status()
                sha256 = hashlib.sha256(await resp.read()).digest()
                source["sha256"] = self._sha256_to_sri(sha256)

    def _generate_source_url(self, version: str, system: str, name: str) -> str:
        (arch, os) = system.split("-", 1)
        if arch == "aarch64":
            arch = "arm64"
        if os == "darwin":
            os = "macos"
        target = f"{os}-{arch}"
        match name:
            case "frida-core" | "frida-gum" | "frida-gumjs":
                file = f"{name}-devkit-{version}-{target}.tar.xz"
            case _:
                raise ValueError(name)
        return f"https://github.com/frida/frida/releases/download/{version}/{file}"

    def _sha256_to_sri(self, sha256: bytes) -> str:
        return "sha256-%s" % base64.b64encode(sha256).decode("utf-8")

    def _hex_encoded_sha256_to_sri(self, sha256: str) -> str:
        return self._sha256_to_sri(bytes.fromhex(sha256))

    def _get_sdist(self, files: list[dict[str, str]]) -> dict[str, Any] | None:
        sdist = filter(lambda file: file.get("packagetype", None) == "sdist", files)
        return next(sdist, None)

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        return tuple(map(int, version.split(".")))

    def _compare_version(self, x: str, y: str) -> int:
        a, b = self._parse_version(x), self._parse_version(y)
        return (a > b) - (a < b)

    def _compare_version_tuple(self, x: tuple[str, ...], y: tuple[str, ...]) -> int:
        return self._compare_version(x[0], y[0])

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
