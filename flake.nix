{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };


  outputs = { self, nixpkgs }:
    let
      systems = [
        "aarch64-linux"
        "x86_64-linux"
      ];

      eachSystem = f:
        nixpkgs.lib.genAttrs systems
          (system: f {
            inherit system;
            pkgs = nixpkgs.legacyPackages.${system};
          });
    in
    {
      overlays.default = import ./overlay.nix { };

      packages = eachSystem ({ system, ... }:
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [
              self.overlays.default
            ];
          };
        in
        {
          inherit (pkgs)
            frida-tools
            ;

          inherit (pkgs.frida)
            frida-core
            frida-gum

            frida-sdk
            frida-toolchain
            ;

          frida-python = pkgs.python3Packages.frida;

          default = pkgs.frida-tools;
        }
      );
    };
}
