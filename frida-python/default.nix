{ lib
, buildPythonPackage
, version
, src
, frida-core
, typing-extensions
}:

buildPythonPackage {
  inherit version src;
  pname = "frida";

  propagatedBuildInputs = [
    typing-extensions
  ];

  buildInputs = [ frida-core ];

  FRIDA_CORE_DEVKIT = frida-core;

  meta = with lib; {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers";
    homepage = "https://www.frida.re/";
    license = licenses.wxWindows;
  };
}
