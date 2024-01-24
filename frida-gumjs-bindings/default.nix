{ lib, fetchNpmDeps }:

fetchNpmDeps {
  src = lib.cleanSourceWith {
    filter = name: type: type == "directory" || !lib.hasSuffix ".nix" (baseNameOf name);
    src = lib.cleanSource ./.;
  };
  hash = "sha256-c0CpRV37NmSR6wbtX2YfAaWonE5+AdU/9Uo2BYk4PJw=";
}
