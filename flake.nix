{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      eachSystem = nixpkgs.lib.genAttrs [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-darwin"
        "x86_64-linux"
      ];
    in
    {
      overlays.default = import ./overlay.nix { };

      packages = eachSystem (system:
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [
              self.overlays.default
            ];
          };
        in
        with pkgs.frida; {
          inherit
            frida-core
            frida-gum
            frida-gumjs

            frida-server
            frida-portal

            frida-tools
            ;

          frida-python = pkgs.python3Packages.frida;

          default = frida-tools;
        }
      );
    };
}
