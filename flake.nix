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
