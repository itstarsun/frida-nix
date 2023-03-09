{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    {
      lib = import ./.;

      flakeModule = ./flake-module.nix;

      templates.default = {
        path = ./templates/flake-parts;
        description = ''
          A template with flake-parts and frida-nix.
        '';
      };

      overlays.default = self.lib.default-overlay;
    }
    // flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system}.extend self.overlays.default;

        apps = [
          "frida"
          "frida-ls-devices"
          "frida-ps"
          "frida-kill"
          "frida-ls"
          "frida-rm"
          "frida-pull"
          "frida-push"
          "frida-discover"
          "frida-trace"
          "frida-join"
          "frida-create"
          "frida-compile"
          "frida-apk"
        ];
      in
      {
        packages = {
          inherit (pkgs)
            frida-core
            frida-gum
            frida-gumjs;
          frida-python = pkgs.python3Packages.frida;
          frida-tools = pkgs.python3Packages.frida-tools;
        };

        apps = (nixpkgs.lib.genAttrs apps (name: flake-utils.lib.mkApp {
          inherit name;
          drv = self.packages.${system}.frida-tools;
        })) // {
          default = self.apps.${system}.frida;
        };

        devShells.default = pkgs.mkShellNoCC {
          packages = with pkgs; [
            (python311.withPackages (p: with p; [
              aiohttp
              black
            ]))
          ];
        };
      }
    );
}
