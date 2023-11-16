{ lib, fetchNpmDeps }:

fetchNpmDeps {
  src = lib.cleanSourceWith {
    filter = name: type: type == "directory" || !lib.hasSuffix ".nix" (baseNameOf name);
    src = lib.cleanSource ./.;
  };
  hash = "sha256-6shXsLsfCQdlU0Y0Z0y/rq5BX8+SCvGJOrt/g8TLTCw=";
}
