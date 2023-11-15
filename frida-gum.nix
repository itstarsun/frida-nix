{ lib
, stdenv
, version
, src

, frida-sdk
, frida-toolchain
, meson
, ninja
, pkg-config
}:

stdenv.mkDerivation {
  pname = "frida-gum";
  inherit version src;
  sourceRoot = "${src.name}/frida-gum";

  outputs = [ "out" "bin" "dev" "lib" ];

  buildInputs = [
    frida-sdk
  ];

  nativeBuildInputs = [
    frida-toolchain
    meson
    ninja
    pkg-config
  ];

  mesonFlags = [
    (lib.mesonOption "default_library" "static")
    (lib.mesonEnable "gumpp" true)
  ];

  strictDeps = true;
}
