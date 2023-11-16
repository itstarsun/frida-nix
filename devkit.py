#!/usr/bin/env python3

import os
import re
import shlex
from collections import OrderedDict
from pathlib import Path
from subprocess import check_output

AR = os.getenv("AR", "ar")
CC = os.getenv("CC", "gcc")
PKG_CONFIG = os.getenv("PKG_CONFIG", "pkg-config")


INCLUDE_PATTERN = re.compile(r'#include\s+[<"](.*?)[>"]')


def generate_header(package: str, umbrella_header: str) -> str:
    cflags = shlex.split(
        check_output([PKG_CONFIG, "--cflags", package], text=True).strip()
    )
    header_dependencies = shlex.split(
        check_output([CC] + cflags + ["-E", "-M", umbrella_header], text=True).strip()
    )[1:]
    header_dependencies = list(filter(lambda x: bool(x.strip()), header_dependencies))
    all_header_files = list(map(Path, header_dependencies))

    if package.startswith("frida-gum"):
        config = """#ifndef GUM_STATIC
# define GUM_STATIC
#endif

"""
    else:
        config = ""

    processed_header_files = set[Path]()
    devkit_header_lines = list[str]()

    def ingest_header(header: Path) -> None:
        nonlocal processed_header_files, devkit_header_lines
        with header.open() as f:
            for line in f:
                match = INCLUDE_PATTERN.match(line.strip())
                if match is not None:
                    name_parts = tuple(match.group(1).split("/"))
                    num_parts = len(name_parts)
                    inline = False
                    for other_header in all_header_files:
                        if other_header.parts[-num_parts:] == name_parts:
                            inline = True
                            if other_header not in processed_header_files:
                                processed_header_files.add(other_header)
                                ingest_header(other_header)
                            break
                    if not inline:
                        devkit_header_lines.append(line)
                else:
                    devkit_header_lines.append(line)

    processed_header_files.add(all_header_files[0])
    ingest_header(all_header_files[0])

    devkit_header = "".join(devkit_header_lines)
    return config + devkit_header


def generate_library(package: str, output: Path) -> None:
    library_flags = shlex.split(
        check_output(
            [PKG_CONFIG, "--static", "--libs", package],
            text=True,
        ).strip()
    )
    library_dirs = infer_library_dirs(library_flags)
    library_names = infer_library_names(library_flags)
    library_paths, extra_flags = resolve_library_paths(library_names, library_dirs)
    extra_flags += infer_linker_flags(library_flags)

    mri = [f"create {output}"]
    for path in library_paths:
        mri.append(f"addlib {path}")
    mri += ["save", "end"]
    check_output([AR, "-M"], input="\n".join(mri), text=True)


def infer_library_dirs(flags: list[str]) -> list[Path]:
    return [Path(flag[2:]) for flag in flags if flag.startswith("-L")]


def infer_library_names(flags: list[str]) -> list[str]:
    return [flag[2:] for flag in flags if flag.startswith("-l")]


def infer_linker_flags(flags: list[str]) -> list[str]:
    return [flag for flag in flags if flag.startswith("-Wl") or flag == "-pthread"]


def resolve_library_paths(
    names: list[str],
    dirs: list[Path],
) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    flags: list[str] = []
    for name in names:
        library_path = None
        for d in dirs:
            candidate = d / f"lib{name}.a"
            if candidate.exists():
                library_path = candidate
                break
        if library_path is not None:
            paths.append(library_path)
        else:
            flags.append(f"-l{name}")
    return (deduplicate(paths), flags)


def deduplicate(items: list[Path]) -> list[Path]:
    return list(OrderedDict.fromkeys(items))


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--output", "-o", type=Path, default=Path("."))
    parser.add_argument("kit", type=str)
    parser.add_argument("include", type=Path)

    args = parser.parse_args()
    package = args.kit + "-1.0"
    match args.kit:
        case "frida-core":
            header = args.include / "frida-1.0" / "frida-core.h"
        case "frida-gum":
            header = args.include / "frida-1.0" / "gum" / "gum.h"
        case "frida-gumjs":
            header = args.include / "frida-1.0" / "gumjs" / "gumjs.h"
        case _:
            raise ValueError(f"unknown kit: {args.kit}")

    output = Path(args.output)

    include = Path(output / "include" / (args.kit + ".h"))
    include.parent.mkdir(parents=True, exist_ok=True)
    include.write_text(generate_header(package, header))

    lib = Path(output / "lib" / ("lib" + args.kit + ".a"))
    lib.parent.mkdir(parents=True, exist_ok=True)
    generate_library(package, lib)
