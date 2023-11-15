{ lib
, stdenv
, newScope
, fetchFromGitHub
}:

let
  version = "16.1.6";
  deps = {
    version = "20230622";
    bundles = {
      x86_64-linux = {
        sdk = "sha256-mM6hEMFQUfi4apeR4UVkNf2Jd4vanfHEyFLAADpx69E=";
        toolchain = "sha256-6FaKEK8YYXnYA+bHk+QSNmud6q0Hac1BuLBQHoSfaFQ=";
      };
    };
  };
in

lib.makeScope newScope (self: with self;
let
  mkFridaBundle = name:
    callPackage ./bundle.nix {
      inherit name;
      inherit (deps) version;
      hash = deps.bundles.${stdenv.system}.${name};
    };
in
{
  src = fetchFromGitHub {
    owner = "frida";
    repo = "frida";
    rev = version;
    hash = "sha256-LLrcJ04wcn6CQ/8NzLdAz6LWyc/jaQgj67bIscMMtMA=";
    fetchSubmodules = true;
  };

  frida-sdk = mkFridaBundle "sdk";
  frida-toolchain = mkFridaBundle "toolchain";
})
