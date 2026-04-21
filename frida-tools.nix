{
  manifest,
  lib,
  fetchurl,
  python3Packages,
}:

let
  version = manifest._tools._version;
  inherit (manifest._tools) url hash;
in

python3Packages.buildPythonPackage {
  pname = "frida-tools";
  inherit version;

  pyproject = true;

  src = fetchurl {
    inherit url hash;
  };

  build-system = [
    python3Packages.setuptools
  ];

  dependencies = with python3Packages; [
    colorama
    frida
    prompt-toolkit
    pygments
    websockets
  ];

  pythonRelaxDeps = [
    "websockets"
  ];

  pythonImportsCheck = [
    "frida_tools"
  ];

  meta = {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers (CLI tools)";
    homepage = "https://www.frida.re/";
    license = with lib.licenses; [
      lgpl2Plus
      wxWindowsException31
    ];
    mainProgram = "frida";
    sourceProvenance = with lib.sourceTypes; [ fromSource ];
  };
}
