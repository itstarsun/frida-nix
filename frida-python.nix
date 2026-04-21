{
  manifest,
  lib,
  stdenv,
  fetchurl,
  python3Packages,
}:

let
  version = manifest._version;
  wheel = manifest.wheels.frida.${stdenv.hostPlatform.system};
in

python3Packages.buildPythonPackage {
  pname = "frida";
  inherit version;

  format = "wheel";

  src = fetchurl {
    inherit (wheel) url hash;
  };

  dependencies =
    with python3Packages;
    lib.optional (!python.pythonAtLeast "3.11") [
      typing-extensions
    ];

  pythonImportsCheck = [
    "frida"
  ];

  meta = {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers (Python bindings)";
    homepage = "https://www.frida.re/";
    license = with lib.licenses; [
      lgpl2Plus
      wxWindowsException31
    ];
    sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
  };
}
