{ lib
, buildPythonPackage
, version
, src
, colorama
, frida
, prompt-toolkit
, pygments
}:

buildPythonPackage {
  inherit version src;
  pname = "frida-tools";

  propagatedBuildInputs = [
    colorama
    frida
    prompt-toolkit
    pygments
  ];

  meta = with lib; {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers";
    homepage = "https://www.frida.re/";
    license = licenses.wxWindows;
  };
}
