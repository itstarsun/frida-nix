{ lib
, buildPythonPackage
, fetchPypi

, version
, hash

, colorama
, frida
, prompt-toolkit
, pygments
}:

buildPythonPackage rec {
  pname = "frida-tools";
  inherit version;

  src = fetchPypi {
    inherit pname version hash;
  };

  propagatedBuildInputs = [
    colorama
    frida
    prompt-toolkit
    pygments
  ];

  pythonImportsCheck = [ "frida_tools" ];

  passthru.updateScript = ./update.py;

  meta = with lib; {
    description = "Dynamic instrumentation toolkit for developers, reverse-engineers, and security researchers (CLI tools)";
    homepage = "https://www.frida.re/";
    license = licenses.wxWindows;
    mainProgram = "frida";
  };
}
