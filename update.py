#!/usr/bin/env python3

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
from typing import NewType, TypedDict, cast

import aiohttp

import pypi


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


class Devkit(StrEnum):
    FRIDA_CORE = "frida-core"
    FRIDA_GUM = "frida-gum"
    FRIDA_GUMJS = "frida-gumjs"

    def download_url_for(self, system: System, version: str) -> str:
        file = f"{self.value}-devkit-{version}-{system.download_name}.tar.xz"
        return f"https://github.com/frida/frida/releases/download/{version}/{file}"


class Metadata(TypedDict, total=False):
    version: str
    sources: dict[str | Devkit, SourceFile | PerSystemSourceFile]


class SourceFile(TypedDict, total=False):
    url: str
    hash: str
    version: str


PerSystemSourceFile = NewType("PerSystemSourceFile", dict[System, SourceFile])


async def update(metadata: Metadata) -> None:
    async with aiohttp.ClientSession() as session:
        pypi_client = pypi.Client(session)

        async with asyncio.TaskGroup() as tg:
            frida_task = tg.create_task(pypi_client.get_project("frida"))
            frida_tools_task = tg.create_task(pypi_client.get_project("frida-tools"))

        frida = frida_task.result()
        frida_tools = frida_tools_task.result()

        assert frida.versions, "frida has no versions"
        assert frida_tools.versions, "frida-tools has no versions"

        version = str(max(frida.versions))
        tools_version = str(max(frida_tools.versions))

        print(f"frida v{version}")
        print(f"frida-tools v{tools_version}")

        if metadata.get("version", version) != version:
            if (sources := metadata.get("sources", None)) is not None:
                sources.clear()

        metadata["version"] = version

        sources = metadata.setdefault("sources", {})

        sources["frida-python"] = py_source_file(frida, version)
        sources["frida-tools"] = py_source_file(frida_tools, tools_version)

        sema = asyncio.BoundedSemaphore(os.cpu_count() or 1)
        async with asyncio.TaskGroup() as tg:
            for devkit in Devkit.__members__.values():
                per_system = cast(PerSystemSourceFile, sources.setdefault(devkit, {}))
                for system in System.__members__.values():
                    source_file = per_system.setdefault(system, {})
                    url = devkit.download_url_for(system, version)
                    if source_file.get("url", url) != url:
                        source_file["hash"] = ""
                    source_file["url"] = url
                    if source_file.get("hash", "") == "":
                        tg.create_task(download_source_file(session, source_file, sema))


def py_source_file(project: pypi.Project, version: str) -> SourceFile:
    sha256 = ""
    for sdist in project.sdist_for(version):
        sha256 = sdist.hashes.get("sha256", "")
        if sha256 != "":
            break
    assert sha256, "no sdist with sha256 found"

    source_file = SourceFile(
        hash=f"sha256-{b64encode(unhexlify(sha256)).decode()}",
    )
    if project.name == "frida-tools":
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

        print(f"downloading {url}", file=sys.stderr)

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
        with open("metadata.json", "rb") as f:
            metadata.update(json.load(f))

    try:
        await update(metadata)
    finally:
        with open("metadata.json", "w+") as f:
            json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
