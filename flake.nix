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
          frida = import ./. { inherit metadata; inherit pkgs; };
          frida' = builtins.removeAttrs frida [ "metadata" ];
        in
        frida' // {
          default = frida.frida-tools;
        }
      );
    };
}
