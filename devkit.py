#!/usr/bin/env python3

import os
import re
import shlex
from collections import OrderedDict
from pathlib import Path
from subprocess import check_output
from tempfile import NamedTemporaryFile

AR = os.getenv("AR", "ar")
CC = os.getenv("CC", "gcc")
NM = os.getenv("NM", "nm")
OBJCOPY = os.getenv("OBJCOPY", "objcopy")
PKG_CONFIG = os.getenv("PKG_CONFIG", "pkg-config")


INCLUDE_PATTERN = re.compile(r'#include\s+[<"](.*?)[>"]')


def generate_header(
    package: str,
    umbrella_header: str,
    thirdparty_symbol_mappings: list[tuple[str, str]],
) -> str:
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

    if len(thirdparty_symbol_mappings) > 0:
        public_mappings: list[tuple[str, str]] = []
        for original, renamed in extract_public_thirdparty_symbol_mappings(
            thirdparty_symbol_mappings
        ):
            public_mappings.append((original, renamed))
            if (
                f"define {original}" not in devkit_header
                and f"define  {original}" not in devkit_header
            ):
                continue

            def fixup_macro(match: re.Match[str]) -> str:
                prefix = match.group(1)
                suffix = re.sub(f"\\b{original}\\b", renamed, match.group(2))
                return f"#undef {original}\n{prefix}{original}{suffix}"

            devkit_header = re.sub(
                r"^([ \t]*#[ \t]*define[ \t]*){0}\b((.*\\\n)*.*)$".format(original),
                fixup_macro,
                devkit_header,
                flags=re.MULTILINE,
            )

        config += "#ifndef __FRIDA_SYMBOL_MAPPINGS__\n"
        config += "#define __FRIDA_SYMBOL_MAPPINGS__\n\n"
        config += (
            "\n".join(
                [
                    f"#define {original} {renamed}"
                    for original, renamed in public_mappings
                ]
            )
            + "\n\n"
        )
        config += "#endif\n\n"

    return config + devkit_header


def generate_library(package: str, output: Path) -> list[tuple[str, str]]:
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

    thirdparty_symbol_mappings = get_thirdparty_symbol_mappings(str(output))
    renames = (
        "\n".join(
            [
                f"{original} {renamed}"
                for original, renamed in thirdparty_symbol_mappings
            ]
        )
        + "\n"
    )
    with NamedTemporaryFile() as renames_file:
        renames_file.write(renames.encode("utf-8"))
        renames_file.flush()
        check_output([OBJCOPY, f"--redefine-syms={renames_file.name}", str(output)])

    return thirdparty_symbol_mappings


def extract_public_thirdparty_symbol_mappings(
    mappings: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    public_prefixes = ["g_", "glib_", "gobject_", "gio_", "gee_", "json_", "cs_"]
    return [
        (original, renamed)
        for original, renamed in mappings
        if any([original.startswith(prefix) for prefix in public_prefixes])
    ]


def get_thirdparty_symbol_mappings(library: str) -> list[tuple[str, str]]:
    return [(name, "_frida_" + name) for name in get_thirdparty_symbol_names(library)]


def get_thirdparty_symbol_names(library: str) -> list[str]:
    visible_names = list(
        set(
            [
                name
                for kind, name in get_symbols(library)
                if kind in ("T", "D", "B", "R", "C")
            ]
        )
    )
    visible_names.sort()

    frida_prefixes = ["frida", "_frida", "gum", "_gum"]
    thirdparty_names = [
        name
        for name in visible_names
        if not any([name.startswith(prefix) for prefix in frida_prefixes])
    ]

    return thirdparty_names


def get_symbols(library: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []

    for line in check_output([NM, library], text=True).strip().split("\n"):
        tokens = line.split(" ")
        if len(tokens) < 3:
            continue
        (kind, name) = tokens[-2:]
        result.append((kind, name))

    return result


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
            umbrella_header = args.include / "frida-1.0" / "frida-core.h"
        case "frida-gum":
            umbrella_header = args.include / "frida-1.0" / "gum" / "gum.h"
        case "frida-gumjs":
            umbrella_header = args.include / "frida-1.0" / "gumjs" / "gumjs.h"
        case _:
            raise ValueError(f"unknown kit: {args.kit}")

    output = Path(args.output)

    lib = Path(output / "lib" / ("lib" + args.kit + ".a"))
    lib.parent.mkdir(parents=True, exist_ok=True)
    thirdparty_symbol_mappings = generate_library(package, lib)

    include = Path(output / "include" / (args.kit + ".h"))
    include.parent.mkdir(parents=True, exist_ok=True)
    include.write_text(
        generate_header(package, umbrella_header, thirdparty_symbol_mappings)
    )
