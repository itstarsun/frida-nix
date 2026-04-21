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
    mkdir -p $out/include $out/lib $out/share/$pname
    tar -xf $src -C $out/share/$pname
    ln -s $out/share/$pname/*.h $out/include
    ln -s $out/share/$pname/*.a $out/lib
    runHook postInstall
  '';

  meta = {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers (SDK)";
    homepage = "https://www.frida.re/";
    license = with lib.licenses; [
      lgpl2Plus
      wxWindowsException31
    ];
    sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
  };
}
