{ stdenv, pname, version, src }:

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
}
