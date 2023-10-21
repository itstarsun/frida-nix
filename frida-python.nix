{ lib
, buildPythonPackage
, fetchPypi

, version
, hash

, frida-core
, typing-extensions
}:

buildPythonPackage rec {
  pname = "frida";
  inherit version;

  src = fetchPypi {
    inherit pname version hash;
  };

  propagatedBuildInputs = [
    typing-extensions
  ];

  postPatch = ''
    export FRIDA_CORE_DEVKIT=${frida-core}/share/frida-core
  '';

  pythonImportsCheck = [ "frida" ];

  meta = with lib; {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers (Python bindings)";
    homepage = "https://www.frida.re/";
    license = licenses.wxWindows;
  };
}
