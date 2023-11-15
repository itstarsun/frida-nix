{ lib, buildNpmPackage, src }:

let
  package = lib.importJSON "${src}/package.json";
in

buildNpmPackage {
  pname = package.name;
  inherit (package) version;

  inherit src;
  npmDepsHash = "sha256-QLeJ4/kC+2a7QQY20c3u1CqLgxuFmz6uc9n4laNAY4g=";

  postInstall = ''
    mkdir -p $out/share/$pname
    mv $out/lib/node_modules/$pname/script-runtime.js $out/share/$pname
    rm -rf $out/lib
  '';
}
