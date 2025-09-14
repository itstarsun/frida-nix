{
  manifest,
  lib,
  system,
  fetchurl,
  python3Packages,
}:

let
  version = manifest._version;
  wheel = manifest.wheels.frida.${system};
in

python3Packages.buildPythonPackage {
  pname = "frida";
  inherit version;

  format = "wheel";

  src = fetchurl {
    inherit (wheel) url hash;
  };

  nativeBuildInputs = [
    python3Packages.pythonRuntimeDepsCheckHook
  ];

  dependencies =
    with python3Packages;
    lib.optional (!python.pythonAtLeast "3.11") [
      typing-extensions
    ];

  pythonImportsCheck = [
    "frida"
  ];

  meta = with lib; {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers (Python bindings)";
    homepage = "https://www.frida.re/";
    license = licenses.wxWindowsException31;
  };
}
