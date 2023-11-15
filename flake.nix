{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };


  outputs = { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
      ];

      eachSystem = f:
        nixpkgs.lib.genAttrs systems
          (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = eachSystem (pkgs:
        let
          frida = pkgs.callPackage ./. { };
        in
        {
          inherit (frida)
            frida-core
            frida-gum

            frida-sdk
            frida-toolchain
            ;
        }
      );
    };
}
