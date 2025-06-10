import argparse
import json
import logging
import re
from asyncio import Future, TaskGroup, gather, run, to_thread
from base64 import b64encode
from binascii import unhexlify
from collections.abc import Callable, Coroutine, Iterable, Iterator
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property, partial, wraps
from hashlib import file_digest
from itertools import product
from operator import itemgetter
from pathlib import Path
from typing import (
    Self,
    TypedDict,
    cast,
)
from urllib.request import Request, urlopen


class NixSystem(StrEnum):
    AARCH64_DARWIN = "aarch64-darwin"
    AARCH64_LINUX = "aarch64-linux"
    X86_64_DARWIN = "x86_64-darwin"
    X86_64_LINUX = "x86_64-linux"

    @cached_property
    def github_arch_os(self) -> tuple[str, str]:
        (arch, os) = self.split("-")
        if arch == "aarch64":
            arch = "arm64"
        if os == "darwin":
            os = "macos"
        return (arch, os)

    @cached_property
    def _wheel_arch_os(self) -> tuple[str, str]:
        (arch, os) = self.split("-")
        if os == "darwin":
            os = "macosx"
            if arch == "aarch64":
                arch = "arm64"
        elif os == "linux":
            os = "manylinux"
        return (arch, os)

    def is_wheel_platform_compatible(self, platform: str) -> bool:
        (arch, os) = self._wheel_arch_os
        return platform.startswith(os) and platform.endswith(arch)


class GitHubArtifact(StrEnum):
    FRIDA_CORE_DEVKIT = "frida-core-devkit"
    FRIDA_GUM_DEVKIT = "frida-gum-devkit"
    FRIDA_GUMJS_DEVKIT = "frida-gumjs-devkit"
    FRIDA_SERVER = "frida-server"
    FRIDA_PORTAL = "frida-portal"

    @property
    def extension(self) -> str:
        match self:
            case GitHubArtifact.FRIDA_SERVER | GitHubArtifact.FRIDA_PORTAL:
                return "xz"
            case _:
                return "tar.xz"

    def download_url_for(self, version: str, system: NixSystem) -> str:
        (arch, os) = system.github_arch_os
        filename = f"{self.value}-{version}-{os}-{arch}.{self.extension}"
        return f"https://github.com/frida/frida/releases/download/{version}/{filename}"  # noqa: E501


class Manifest(TypedDict):
    _version: str
    _tools: "Tools"
    wheels: dict[str, dict[str, "DownloadedFile"]]
    artifacts: dict[str, dict[str, "DownloadedFile"]]


class Tools(TypedDict):
    _version: str
    hash: str


class DownloadedFile(TypedDict):
    url: str
    hash: str


def main() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force update even if the manifest is up-to-date",
    )
    parser.add_argument(
        "-m",
        "--manifest",
        type=Path,
        default="manifest.json",
        help="path to manifest file (default: %(default)s)",
    )
    parser.add_argument(
        "version",
        nargs="?",
        default="latest",
        help="frida version (default: %(default)s)",
    )
    parser.add_argument(
        "tools_version",
        metavar="tools version",
        nargs="?",
        default="latest",
        help="frida-tools version (default: %(default)s)",
    )

    args = parser.parse_args()
    manifest_path = cast("Path", args.manifest)

    old_manifest = None
    if not args.force:
        with suppress(FileNotFoundError), manifest_path.open("r") as f:
            old_manifest = json.load(f)

    new_manifest = run(_update(args.version, args.tools_version, old_manifest))
    if new_manifest != old_manifest:
        with manifest_path.open("w+") as f:
            json.dump(new_manifest, f, indent=2, sort_keys=True)
            f.write("\n")


async def _update(
    version: str,
    tools_version: str,
    old_manifest: Manifest | None,
) -> Manifest:
    (frida, frida_tools) = await gather(
        pypi_get_project("frida"),
        pypi_get_project("frida-tools"),
    )

    version = _select_version(frida, version)
    tools_version = _select_version(frida_tools, tools_version)

    tools_sdist_hash = None
    wheels = None
    artifacts = None

    with suppress(Exception):
        if old_manifest is not None:
            if old_manifest["_version"] == version:
                wheels = _ready(old_manifest["wheels"])
                artifacts = _ready(old_manifest["artifacts"])
            if old_manifest["_tools"]["_version"] == tools_version:
                tools_sdist_hash = _ready(old_manifest["_tools"]["hash"])
            if (
                artifacts is not None
                and wheels is not None
                and tools_sdist_hash is not None
            ):
                return old_manifest

    async with TaskGroup() as tg:
        if tools_sdist_hash is None:
            tools_sdist_hash = tg.create_task(
                download_sdist_file_for(frida_tools, tools_version)
            )
        if wheels is None:
            wheels = tg.create_task(_download_frida_wheels(frida, version))
        if artifacts is None:
            artifacts = tg.create_task(_download_artifacts(version))

    return Manifest(
        _version=version,
        _tools=Tools(
            _version=tools_version,
            hash=tools_sdist_hash.result(),
        ),
        artifacts=artifacts.result(),
        wheels=wheels.result(),
    )


def _ready[T](value: T) -> Future[T]:
    future = Future[T]()
    future.set_result(value)
    return future


async def _download_frida_wheels(
    project: "PyPIProject",
    version: str,
) -> dict[str, dict[str, DownloadedFile]]:
    return {
        "frida": await _download_wheel_files_for(project, version),
    }


def _select_version(
    project: "PyPIProject",
    wanted_version: str,
) -> str:
    versions = project["versions"]
    if wanted_version == "latest":
        # Note that we cannot use versions[-1] because PEP 700 states that
        # the order of the versions field is not significant.
        # See https://peps.python.org/pep-0700/#versions.
        return max(versions, key=_parse_version)
    elif wanted_version not in versions:
        raise ValueError(f"{project['name']}@{wanted_version} is not found")
    else:
        return wanted_version


def _parse_version(version: str) -> tuple[int, int, int]:
    tokens = version.split(".")
    if len(tokens) != 3 or not all(map(str.isnumeric, tokens)):
        raise ValueError(f"invalid version: {version}")
    (major, minor, patch) = tuple(map(int, tokens))
    return (major, minor, patch)


async def _download_artifacts(
    version: str,
) -> dict[str, dict[str, DownloadedFile]]:
    download_files = await gather(
        *(
            _download_artifact_for(version, artifact, system)
            for artifact, system in product(
                GitHubArtifact.__members__.values(),
                NixSystem.__members__.values(),
            )
        )
    )
    result: dict[str, dict[str, DownloadedFile]] = {}
    for (artifact, system), download_file in zip(
        product(GitHubArtifact, NixSystem),
        download_files,
        strict=True,
    ):
        result.setdefault(artifact, {})[system] = download_file
    return result


async def _download_artifact_for(
    version: str,
    artifact: GitHubArtifact,
    system: NixSystem,
) -> DownloadedFile:
    url = artifact.download_url_for(version, system)
    return DownloadedFile(url=url, hash=await download_file(url))


async def _download_wheel_files_for(
    project: "PyPIProject",
    version: str,
) -> dict[str, DownloadedFile]:
    wheel_files = [
        (_ParsedWheelFilename.parse(wheel_file["filename"]), wheel_file)
        for wheel_file in pypi_wheel_files_for(project, version)
    ]
    if len(wheel_files) == 0:
        raise ValueError(f"{project['name']}@{version} has no wheel files")

    # Sort wheel files by parsed filenames, which takes platform versions
    # into account.
    wheel_files.sort(key=itemgetter(0))

    downloaded_files = await gather(
        *(
            _download_wheel_file_for(wheel_files, system)
            for system in NixSystem
        )
    )
    return dict(zip(NixSystem, downloaded_files, strict=True))


async def _download_wheel_file_for(
    files: Iterable[tuple["_ParsedWheelFilename", "PyPIFile"]],
    system: NixSystem,
) -> DownloadedFile:
    for filename, file in files:
        for platform in filename.platforms:
            if system.is_wheel_platform_compatible(platform):
                return DownloadedFile(
                    url=file["url"],
                    hash=await download_pypi_file(file),
                )
    raise ValueError(f"no wheel file found for {system}")


_MANYLINUX_LEGACY_ALIASES = {
    "manylinux1_x86_64": "manylinux_2_5_x86_64",
    "manylinux1_i686": "manylinux_2_5_i686",
    "manylinux2010_x86_64": "manylinux_2_12_x86_64",
    "manylinux2010_i686": "manylinux_2_12_i686",
    "manylinux2014_x86_64": "manylinux_2_17_x86_64",
    "manylinux2014_i686": "manylinux_2_17_i686",
    "manylinux2014_aarch64": "manylinux_2_17_aarch64",
    "manylinux2014_armv7l": "manylinux_2_17_armv7l",
    "manylinux2014_ppc64": "manylinux_2_17_ppc64",
    "manylinux2014_ppc64le": "manylinux_2_17_ppc64le",
    "manylinux2014_s390x": "manylinux_2_17_s390x",
}


def _platform_cmp_key(platform: str) -> tuple[str, int, int, str]:
    m = re.search(r"([^_]+)_([0-9]+)_([0-9]+)_(.+)", platform)
    if m is None:
        return (platform, 0, 0, "")
    (os, major, minor, arch) = m.groups()
    return (os, int(major), int(minor), arch)


@dataclass
class _ParsedWheelFilename:
    name: str
    interpreters: list[str]
    abis: list[str]
    platforms: list[str]

    def __post_init__(self) -> None:
        self._cmp_key = (
            self.name,
            self.interpreters,
            self.abis,
            list(map(_platform_cmp_key, self.platforms)),
        )

    @classmethod
    def parse(cls, filename: str) -> Self:
        (*name, interpreters, abis, platforms) = filename.split("-")
        return cls(
            "-".join(name),
            interpreters.split("."),
            abis.split("."),
            [
                _MANYLINUX_LEGACY_ALIASES.get(platform, platform)
                for platform in platforms.split(".")
            ],
        )

    def __lt__(self, other: Self) -> bool:
        return self._cmp_key < other._cmp_key


def asyncify[**P, T](
    func: Callable[P, T],
) -> Callable[P, Coroutine[None, None, T]]:
    return wraps(func)(partial(to_thread, func))


"""
Utility functions for downloading files and returning their SRI hashes.
"""


async def download_sdist_file_for(project: "PyPIProject", version: str) -> str:
    (sdist_file, *rest) = pypi_sdist_files_for(project, version)
    if len(rest) != 0:
        logging.warning(
            "found multiple sdist files for %s@%s",
            project["name"],
            version,
        )
    return await download_pypi_file(sdist_file)


async def download_pypi_file(file: "PyPIFile") -> str:
    if (hexdigest := file["hashes"].get("sha256")) is not None:
        return _sha256_digest_to_sri(unhexlify(hexdigest))
    # This is unlikely to happen, but just in case.
    return await download_file(file["url"])


@asyncify
def download_file(url: str) -> str:
    logging.info("downloading %s", url)
    with urlopen(url) as f:
        digest = file_digest(f, "sha256").digest()
        return _sha256_digest_to_sri(digest)


def _sha256_digest_to_sri(digest: bytes) -> str:
    return f"sha256-{b64encode(digest).decode()}"


"""
A simple PyPI client implementation using the simple repository API,
the client assumes that the server supports API version 1.1 or later.

See https://packaging.python.org/en/latest/specifications/simple-repository-api/
for details.
"""  # noqa: E501


class PyPIProject(TypedDict):
    name: str
    files: list["PyPIFile"]
    versions: list[str]  # api-version >= 1.1


class PyPIFile(TypedDict):
    filename: str
    url: str
    hashes: dict[str, str]


@asyncify
def pypi_get_project(name: str) -> PyPIProject:
    req = Request(f"https://pypi.org/simple/{name}/")
    req.add_header("Accept", "application/vnd.pypi.simple.v1+json")
    with urlopen(req) as resp:
        data = json.load(resp)
        assert data["meta"]["api-version"] != "1.0", (
            "API version 1.0 is not supported"
        )
        return cast("PyPIProject", data)


def pypi_files_for(project: PyPIProject, version: str) -> Iterator[PyPIFile]:
    prefix = f"{project['name']}-{version}"
    for file in project["files"]:
        if file["filename"].startswith(prefix):
            yield file


def pypi_sdist_files_for(
    project: PyPIProject, version: str
) -> Iterator[PyPIFile]:
    for file in pypi_files_for(project, version):
        if file["filename"].endswith((".tar.gz", ".zip")):
            yield file


def pypi_wheel_files_for(
    project: PyPIProject, version: str
) -> Iterator[PyPIFile]:
    for file in pypi_files_for(project, version):
        if file["filename"].endswith(".whl"):
            yield file


if __name__ == "__main__":
    main()
