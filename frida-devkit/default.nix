{ lib
, stdenvNoCC
, pname
, version
, src
}:

stdenvNoCC.mkDerivation {
  inherit pname version src;

  sourceRoot = ".";

  installPhase = ''
    mkdir -p $out/include $out/lib
    cp *.h $out/include
    cp *.a $out/lib
  '';

  meta = with lib; {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers";
    homepage = "https://www.frida.re/";
    license = licenses.wxWindows;
  };
}
