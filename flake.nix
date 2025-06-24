{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs?ref=nixpkgs-unstable";
  };

  outputs =
    { self, nixpkgs }:

    let
      inherit (nixpkgs) lib;

      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-darwin"
        "x86_64-linux"
      ];

      eachSystem = lib.genAttrs systems;
    in
    {
      overlays.default = import ./overlay.nix;

      packages = eachSystem (
        system:

        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [
              self.overlays.default
            ];
          };
        in

        lib.filterAttrs (lib.const lib.isDerivation) pkgs.fridaPackages
        // {
          default = pkgs.frida-tools;

          update = pkgs.writers.writePython3Bin "update" {
            libraries = [ pkgs.python3Packages.packaging ];
          } ./update.py;
        }
      );
    };
}
