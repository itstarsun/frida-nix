{ lib
, system
, newScope
, fetchurl
, python3Packages
, manifest ? lib.importJSON ./manifest.json
}:

lib.makeScope newScope (self: with self;
let
  version = manifest._version;
  inherit (manifest) artifacts;

  mkFridaDevkitOrBinary = path: pname:
    callPackage path {
      inherit pname version;
      src = fetchurl {
        inherit (artifacts.${pname}.${system}) url hash;
      };
    };

  mkFridaDevkit = mkFridaDevkitOrBinary ./frida-devkit.nix;
  mkFridaBinary = mkFridaDevkitOrBinary ./frida-binary.nix;

  devkits = lib.genAttrs [ "frida-core-devkit" "frida-gum-devkit" "frida-gumjs-devkit" ] mkFridaDevkit;
  binaries = lib.genAttrs [ "frida-server" "frida-portal" ] mkFridaBinary;
in
devkits // binaries // {
  inherit manifest;

  frida-core = devkits.frida-core-devkit;
  frida-gum = devkits.frida-gum-devkit;
  frida-gumjs = devkits.frida-gumjs-devkit;

  frida-python = callPackage ./frida-python.nix {
    inherit python3Packages;
  };

  frida-tools = callPackage ./frida-tools.nix {
    inherit python3Packages;
  };
})
