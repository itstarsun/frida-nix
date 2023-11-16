{ stdenv
, drv
, kit
, frida-toolchain
, pkg-config
, python3
}:

stdenv.mkDerivation {
  pname = "${drv.pname}-devkit";
  inherit (drv) version;

  unpackPhase = ''
    cp ${./devkit.py} devkit.py
  '';

  postPatch = ''
    patchShebangs devkit.py
  '';

  buildPhase = ''
    ./devkit.py -o $out ${kit} ${drv.dev}/include
  '';

  buildInputs = [ drv ] ++ drv.buildInputs;

  nativeBuildInputs = [
    frida-toolchain
    pkg-config
    python3
  ];

  strictDeps = true;
}
