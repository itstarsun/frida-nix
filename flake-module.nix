{ lib, flake-parts-lib, ... }:
let
  inherit (flake-parts-lib) mkPerSystemOption;
  inherit (lib) mkOption types;

  frida = import ./.;
in
{
  options = {
    perSystem = mkPerSystemOption ({ config, pkgs, ... }:
      let
        cfg = config.frida;
      in
      {
        options = {
          frida = {
            version = mkOption {
              type = types.str;
              default = cfg.metadata.latest-release;
            };

            tools-version = mkOption {
              type = types.str;
              default = cfg.metadata.latest-tools;
            };

            metadata = mkOption {
              type = types.raw;
              default = frida.default-metadata;
            };

            build = {
              pkgs = mkOption {
                type = types.raw;
              };

              frida-core = mkOption {
                type = types.package;
                default = cfg.build.pkgs.frida-core;
              };

              frida-gum = mkOption {
                type = types.package;
                default = cfg.build.pkgs.frida-gum;
              };

              frida-gumjs = mkOption {
                type = types.package;
                default = cfg.build.pkgs.frida-gumjs;
              };

              frida-python = mkOption {
                type = types.package;
                default = cfg.build.pkgs.python3Packages.frida;
              };

              frida-tools = mkOption {
                type = types.package;
                default = cfg.build.pkgs.python3Packages.frida-tools;
              };
            };
          };
        };

        config = {
          frida.build.pkgs = pkgs.extend (frida.mkOverlay {
            inherit (cfg) metadata version tools-version;
          });

          _module.args.frida = cfg.build;
        };
      });
  };
}
