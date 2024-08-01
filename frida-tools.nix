{ manifest
, lib
, fetchPypi
, python3Packages
}:

let
  version = manifest._tools._version;
  inherit (manifest._tools) hash;
in

python3Packages.buildPythonPackage rec {
  pname = "frida-tools";
  inherit version;

  src = fetchPypi {
    inherit pname version hash;
  };

  dependencies = with python3Packages; [
    colorama
    frida
    prompt-toolkit
    pygments
  ];

  pythonImportsCheck = [
    "frida_tools"
  ];

  meta = with lib; {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers (CLI tools)";
    homepage = "https://www.frida.re/";
    license = licenses.wxWindows;
    mainProgram = "frida";
  };
}
