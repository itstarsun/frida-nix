{ lib
, stdenv
, callPackage
, version
, src

, frida-sdk
, frida-toolchain
, meson
, ninja
, nodejs
, npmHooks
, pkg-config
, python3
}:

let
  frida-gumjs-bindings = callPackage ./frida-gumjs-bindings { };
in

stdenv.mkDerivation {
  pname = "frida-gum";
  inherit version src;
  sourceRoot = "${src.name}/frida-gum";

  outputs = [ "out" "bin" "dev" "lib" ];

  postPatch = ''
    patchShebangs .

    mkdir -p build/bindings/gumjs
    cp ${frida-gumjs-bindings}/package-lock.json build/bindings/gumjs
  '';

  npmRoot = "build/bindings/gumjs";
  npmDeps = frida-gumjs-bindings;

  disallowedReferences = [
    frida-gumjs-bindings
  ];

  buildInputs = [
    frida-sdk
  ];

  nativeBuildInputs = [
    frida-toolchain
    meson
    ninja
    nodejs
    npmHooks.npmConfigHook
    pkg-config
    python3
  ];

  mesonFlags = [
    (lib.mesonOption "default_library" "static")
    (lib.mesonEnable "gumjs" true)
    (lib.mesonEnable "gumpp" true)
  ];

  strictDeps = true;
}
