{
  lib,
  system,
  newScope,
  fetchurl,
  python3Packages,
  manifest ? lib.importJSON ./manifest.json,
}:

lib.makeScope newScope (
  self:
  let
    version = self.manifest._version;
    inherit (self.manifest) artifacts;

    mkFridaDevkitOrBinary =
      path: pname:
      self.callPackage path {
        inherit pname version;
        src = fetchurl {
          inherit (artifacts.${pname}.${system}) url hash;
        };
      };

    mkFridaDevkit = mkFridaDevkitOrBinary ./frida-devkit.nix;
    mkFridaBinary = mkFridaDevkitOrBinary ./frida-binary.nix;

    devkits = lib.genAttrs [
      "frida-core-devkit"
      "frida-gum-devkit"
      "frida-gumjs-devkit"
    ] mkFridaDevkit;
    binaries = lib.genAttrs [ "frida-server" "frida-portal" ] mkFridaBinary;
  in
  devkits
  // binaries
  // {
    inherit manifest;

    frida-core = self.frida-core-devkit;
    frida-gum = self.frida-gum-devkit;
    frida-gumjs = self.frida-gumjs-devkit;

    frida-python = self.callPackage ./frida-python.nix {
      inherit python3Packages;
    };

    frida-tools = self.callPackage ./frida-tools.nix {
      inherit python3Packages;
    };
  }
)
