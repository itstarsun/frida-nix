{
  inputs = {
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";

    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    frida-nix.url = "github:itstarsun/frida-nix";
    frida-nix.inputs.nixpkgs-lib.follows = "nixpkgs";
  };

  outputs = inputs:
    inputs.flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.frida-nix.flakeModule
      ];

      systems = [
        "x86_64-linux"
      ];

      perSystem = { config, ... }: {
        packages = {
          inherit (config.frida.build)
            frida-core
            frida-gum
            frida-gumjs
            frida-python
            frida-tools;
        };
      };
    };
}
