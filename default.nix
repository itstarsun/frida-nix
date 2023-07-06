{ metadata ? builtins.fromJSON (builtins.readFile ./metadata.json)
, pkgs
, lib ? pkgs.lib
, system ? pkgs.system
}:

let
  inherit (metadata) version;

  withBaseAttrs = drv: drv.overrideAttrs (oldAttrs:
    let
      baseAttrs = {
        meta = with lib; {
          description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers";
          homepage = "https://www.frida.re/";
          license = licenses.wxWindows;
        };
      };
    in
    lib.recursiveUpdate baseAttrs oldAttrs);

  mkFridaDevkit = pname: withBaseAttrs (pkgs.callPackage ./frida-devkit.nix {
    inherit pname version;
    src = pkgs.fetchurl metadata.sources.${pname}.${system};
  });

  mkFridaBinary = pname: withBaseAttrs (pkgs.callPackage ./frida-binary.nix {
    inherit pname version;
    src = pkgs.fetchurl metadata.sources.${pname}.${system};
  });

  mkFridaPython = lib.makeOverridable ({ pythonPackages, frida-core }:
    withBaseAttrs (pythonPackages.callPackage ./frida-python.nix {
      inherit version frida-core;
      inherit (metadata.sources.frida-python) hash;
    }));

  mkFridaTools = lib.makeOverridable ({ pythonPackages, ... } @ args:
    withBaseAttrs (pythonPackages.callPackage ./frida-tools.nix {
      inherit (metadata.sources.frida-tools) version hash;
      frida = frida-python.override args;
    }));

  devkits = lib.genAttrs [ "frida-core" "frida-gum" "frida-gumjs" ] mkFridaDevkit;
  binarys = lib.genAttrs [ "frida-server" "frida-portal" ] mkFridaBinary;

  pythonArgs = {
    pythonPackages = pkgs.python3.pkgs;
    frida-core = devkits.frida-core;
  };

  frida-python = mkFridaPython pythonArgs;
  frida-tools = mkFridaTools pythonArgs;
in

devkits // binarys // {
  inherit
    frida-python
    frida-tools
    metadata
    ;
}
