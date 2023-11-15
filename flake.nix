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
          (system: f nixpkgs.legacyPackages.${system});
    in
    {
      overlays.default = import ./overlay.nix;

      packages = eachSystem (pkgs:
        let
          frida = pkgs.callPackage ./. { };
        in
        {
          inherit (frida)
            frida-core
            frida-gum

            frida-python
            frida-tools

            frida-sdk
            frida-toolchain
            ;

          default = frida.frida-tools;
        }
      );
    };
}
