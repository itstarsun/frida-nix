{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      metadata = builtins.fromJSON (builtins.readFile ./metadata.json);

      eachSystem = nixpkgs.lib.genAttrs [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-darwin"
        "x86_64-linux"
      ];
    in
    {
      overlays.default = import ./overlay.nix metadata;

      packages = eachSystem (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          frida = pkgs.callPackage ./. { inherit metadata; };
        in
        {
          inherit (frida)
            frida-core
            frida-gum
            frida-gumjs
            frida-python
            frida-tools
            ;

          default = frida.frida-tools;
        }
      );
    };
}
