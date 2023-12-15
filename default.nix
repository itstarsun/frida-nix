{ lib
, stdenv
, newScope
, fetchFromGitHub
, python3Packages
, symlinkJoin

, metadata ? builtins.fromJSON (builtins.readFile ./metadata.json)
}:

let
  inherit (metadata)
    version
    repo
    tools
    barebone
    compiler
    deps
    ;
in

lib.makeScope newScope (self: with self;
let
  mkFridaBundle = name:
    callPackage ./bundle.nix {
      inherit name;
      inherit (deps) version;
      hash = deps.bundles.${stdenv.system}.${name};
    };

  mkFridaDevkit = { drv, kit ? drv.pname }:
    callPackage ./devkit.nix {
      inherit drv kit;
    };
in
{
  src = fetchFromGitHub {
    owner = "frida";
    repo = "frida";
    rev = version;
    hash = repo;
    fetchSubmodules = true;
  };

  frida-core = callPackage ./frida-core.nix {
    inherit version barebone compiler;
  };
  frida-gum = callPackage ./frida-gum.nix {
    inherit version;
  };

  frida-core-devkit = mkFridaDevkit { drv = frida-core; };
  frida-gum-devkit = mkFridaDevkit { drv = frida-gum; };
  frida-gumjs-devkit = mkFridaDevkit { drv = frida-gum; kit = "frida-gumjs"; };

  frida-python = callPackage ./frida-python.nix {
    inherit version;
    inherit (python3Packages)
      buildPythonPackage
      python
      typing-extensions
      ;
  };
  frida-tools = python3Packages.callPackage ./frida-tools.nix {
    inherit (tools) version hash;
    frida = frida-python;
  };

  frida-sdk = mkFridaBundle "sdk";
  frida-toolchain = mkFridaBundle "toolchain";

  frida-sdk-with-toolchain = symlinkJoin {
    name = "frida-sdk-with-toolchain";
    paths = [
      frida-sdk
      frida-toolchain
    ];
  };
})
