{ metadata ? builtins.fromJSON (builtins.readFile ./metadata.json)
, lib
, system
, newScope
, fetchurl
, python3Packages
}:

lib.makeScope newScope (self: with self;
let
  inherit (metadata) version sources;

  mkFridaDevkitOrBinary = path: pname:
    callPackage path {
      inherit pname version;
      src = fetchurl {
        inherit (sources.${pname}.${system}) url hash;
      };
    };

  mkFridaDevkit = mkFridaDevkitOrBinary ./frida-devkit.nix;
  mkFridaBinary = mkFridaDevkitOrBinary ./frida-binary.nix;

  devkits = lib.genAttrs [ "frida-core" "frida-gum" "frida-gumjs" ] mkFridaDevkit;
  binaries = lib.genAttrs [ "frida-server" "frida-portal" ] mkFridaBinary;
in
devkits // binaries // {
  inherit metadata;

  frida-python = python3Packages.callPackage ./frida-python.nix {
    inherit version frida-core;
    inherit (sources.frida-python) hash;
  };

  frida-tools = python3Packages.callPackage ./frida-tools.nix {
    inherit (sources.frida-tools) version hash;
    frida = frida-python;
  };
})
