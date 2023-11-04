#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p "python3.withPackages (p: with p; [ aiohttp packaging ])"

from __future__ import annotations

import asyncio
import json
import os
import sys
from base64 import b64encode
from binascii import unhexlify
from contextlib import suppress
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Iterator, NewType, TypedDict, cast

import aiohttp
from packaging.version import Version

METADATA = Path(__file__).parent / "metadata.json"


class System(StrEnum):
    AARCH64_DARWIN = "aarch64-darwin"
    AARCH64_LINUX = "aarch64-linux"
    X86_64_DARWIN = "x86_64-darwin"
    X86_64_LINUX = "x86_64-linux"

    @property
    def download_name(self) -> str:
        match self:
            case System.AARCH64_DARWIN:
                return "macos-arm64"
            case System.AARCH64_LINUX:
                return "linux-arm64"
            case System.X86_64_DARWIN:
                return "macos-x86_64"
            case System.X86_64_LINUX:
                return "linux-x86_64"


class Prebuilt(StrEnum):
    FRIDA_CORE = "frida-core"
    FRIDA_GUM = "frida-gum"
    FRIDA_GUMJS = "frida-gumjs"
    FRIDA_SERVER = "frida-server"
    FRIDA_PORTAL = "frida-portal"

    def download_file_for(self, system: System, version: str) -> str:
        match self:
            case Prebuilt.FRIDA_CORE | Prebuilt.FRIDA_GUM | Prebuilt.FRIDA_GUMJS:
                return f"{self.value}-devkit-{version}-{system.download_name}.tar.xz"
            case Prebuilt.FRIDA_SERVER | Prebuilt.FRIDA_PORTAL:
                return f"{self.value}-{version}-{system.download_name}.xz"

    def download_url_for(self, system: System, version: str) -> str:
        file = self.download_file_for(system, version)
        return f"https://github.com/frida/frida/releases/download/{version}/{file}"


class Metadata(TypedDict, total=False):
    version: str
    sources: dict[str | Prebuilt, SourceFile | PerSystemSourceFile]


class SourceFile(TypedDict, total=False):
    url: str
    hash: str
    version: str


PerSystemSourceFile = NewType("PerSystemSourceFile", dict[System, SourceFile])


class PyPIProject(TypedDict):
    name: str
    files: list[PyPIFile]
    versions: list[str]


class PyPIFile(TypedDict):
    filename: str
    url: str
    hashes: dict[str, str]


async def get_pypi_project(session: aiohttp.ClientSession, name: str) -> PyPIProject:
    async with session.get(
        f"https://pypi.org/simple/{name}/",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    ) as resp:
        resp.raise_for_status()
        return cast(PyPIProject, await resp.json())


def pypi_files_for(project: PyPIProject, version: Version | str) -> Iterator[PyPIFile]:
    prefix = f'{project["name"]}-{version}'
    for file in project["files"]:
        filename = file["filename"]
        if not filename.startswith(prefix):
            continue
        suffix = filename[len(prefix) :]
        if suffix == "" or suffix.startswith(("-", ".")):
            yield file


def pypi_sdist_for(project: PyPIProject, version: Version | str) -> Iterator[PyPIFile]:
    for file in pypi_files_for(project, version):
        if file["filename"].endswith((".tar.gz", ".zip")):
            yield file


async def update(metadata: Metadata) -> None:
    async with aiohttp.ClientSession() as session:
        async with asyncio.TaskGroup() as tg:
            frida_task = tg.create_task(get_pypi_project(session, "frida"))
            frida_tools_task = tg.create_task(get_pypi_project(session, "frida-tools"))

        frida = frida_task.result()
        frida_tools = frida_tools_task.result()

        assert frida.get("versions", None), "frida has no versions"
        assert frida_tools.get("versions", None), "frida-tools has no versions"

        version = str(max(map(Version, frida["versions"])))
        tools_version = str(max(map(Version, frida_tools["versions"])))

        print(f"frida v{version}", flush=True)
        print(f"frida-tools v{tools_version}", flush=True)

        if metadata.get("version", version) != version:
            if (sources := metadata.get("sources", None)) is not None:
                sources.clear()

        metadata["version"] = version

        sources = metadata.setdefault("sources", {})

        sources["frida-python"] = py_source_file(frida, version)
        sources["frida-tools"] = py_source_file(frida_tools, tools_version)

        sema = asyncio.BoundedSemaphore(os.cpu_count() or 1)
        async with asyncio.TaskGroup() as tg:
            for prebuilt in Prebuilt.__members__.values():
                per_system = cast(PerSystemSourceFile, sources.setdefault(prebuilt, {}))
                for system in System.__members__.values():
                    source_file = per_system.setdefault(system, {})
                    url = prebuilt.download_url_for(system, version)
                    if source_file.get("url", url) != url:
                        source_file["hash"] = ""
                    source_file["url"] = url
                    if source_file.get("hash", "") == "":
                        tg.create_task(download_source_file(session, source_file, sema))


def py_source_file(project: PyPIProject, version: str) -> SourceFile:
    sha256 = ""
    for file in pypi_sdist_for(project, version):
        sha256 = file["hashes"].get("sha256", sha256)
    assert sha256, "no sdist with sha256 found"
    source_file = SourceFile(hash=f"sha256-{b64encode(unhexlify(sha256)).decode()}")
    if project["name"] == "frida-tools":
        source_file["version"] = version
    return source_file


async def download_source_file(
    session: aiohttp.ClientSession,
    source_file: SourceFile,
    sema: asyncio.BoundedSemaphore,
) -> None:
    async with sema:
        url = source_file.get("url", None)
        assert url

        print(f"downloading {url}", file=sys.stderr, flush=True)

        resp = await session.get(url)
        resp.raise_for_status()

        hash = sha256()
        while True:
            data = await resp.content.readany()
            if not data:
                break
            hash.update(data)

        source_file["hash"] = f"sha256-{b64encode(hash.digest()).decode()}"


async def main() -> None:
    metadata = Metadata()
    with suppress(FileNotFoundError):
        with open(METADATA, "rb") as f:
            metadata.update(json.load(f))

    try:
        await update(metadata)
    finally:
        with open(METADATA, "w+") as f:
            json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
