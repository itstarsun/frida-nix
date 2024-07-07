{ lib
, hostPlatform
, buildPythonPackage
, fetchPypi

, version
, wheels

, python3
, typing-extensions
}:

let
  wheel = wheels.${hostPlatform.system};
in

buildPythonPackage rec {
  pname = "frida";
  inherit version;

  format = "wheel";

  src = fetchPypi {
    inherit pname version format;
    inherit (wheel) python platform hash;
    dist = wheel.python;
    abi = "abi3";
  };

  propagatedBuildInputs = lib.optional (!python3.pythonAtLeast "3.11") [
    typing-extensions
  ];

  pythonImportsCheck = [ "frida" ];

  meta = with lib; {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers (Python bindings)";
    homepage = "https://www.frida.re/";
    license = licenses.wxWindows;
  };
}
