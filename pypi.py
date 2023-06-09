from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass
from functools import wraps
from typing import Any, Iterator, TypeVar, dataclass_transform
from urllib.parse import urljoin

import aiohttp
from packaging.utils import canonicalize_name
from packaging.version import Version

_T = TypeVar("_T")


@dataclass_transform(kw_only_default=True)
def _dataclass(cls: type[_T]) -> type[_T]:
    cls = dataclass(kw_only=True)(cls)

    @wraps(cls.__init__)
    def __init__(self: _T, **kwargs: Any) -> None:
        assert is_dataclass(self)
        for name, value in tuple(kwargs.items()):
            if value is None or name not in self.__dataclass_fields__:  # type: ignore
                del kwargs[name]
        __init__.__wrapped__(self, **kwargs)  # type: ignore

    cls.__init__ = __init__  # type: ignore
    return cls


@_dataclass
class Project:
    name: str = ""
    files: list[File] = field(default_factory=list)
    versions: list[Version] = field(default_factory=list)

    def __post_init__(self) -> None:
        for i, file in enumerate(self.files):
            if isinstance(file, dict):
                self.files[i] = File(**file)
        for i, version in enumerate(self.versions):
            if isinstance(version, str):
                self.versions[i] = Version(version)
        self.versions = sorted(self.versions)

    def files_for(self, version: Version | str) -> Iterator[File]:
        prefix = f"{self.name}-{version}"
        for file in self.files:
            if not file.filename.startswith(prefix):
                continue
            suffix = file.filename[len(prefix) :]
            if suffix == "" or suffix.startswith(("-", ".")):
                yield file

    def sdist_for(self, version: Version | str) -> Iterator[File]:
        # TODO(https://github.com/python/mypy/issues/8085#issuecomment-1436218589): File.is_sdist.fget
        return filter(lambda file: file.is_sdist, self.files_for(version))


@_dataclass
class File:
    filename: str = ""
    url: str = ""
    hashes: dict[str, str] = field(default_factory=dict)

    @property
    def is_sdist(self) -> bool:
        return self.filename.endswith((".tar.gz", ".zip"))


@dataclass
class Client:
    session: aiohttp.ClientSession
    base_url: str = "https://pypi.org/simple/"

    async def get_project(self, name: str) -> Project:
        resp = await self.session.get(
            urljoin(self.base_url, canonicalize_name(name)),
            headers={
                "Accept": "application/vnd.pypi.simple.v1+json",
            },
        )
        resp.raise_for_status()
        return Project(**await resp.json())


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        async with aiohttp.ClientSession() as session:
            client = Client(session)
            project = await client.get_project("frida")
            print("\n".join(map(str, project.versions)))

    asyncio.run(main())
