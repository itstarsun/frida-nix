{
  lib,
  stdenv,
  pname,
  version,
  src,
}:

stdenv.mkDerivation {
  inherit pname version src;

  dontUnpack = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out/bin
    unxz $src --stdout > $out/bin/$pname
    chmod +x $out/bin/$pname
    runHook postInstall
  '';

  meta = {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers";
    homepage = "https://www.frida.re/";
    license = with lib.licenses; [
      lgpl2Plus
      wxWindowsException31
    ];
    sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
  };
}
