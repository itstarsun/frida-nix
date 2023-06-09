{ version
, hash

, buildPythonPackage
, fetchPypi

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

  configurePhase = ''
    runHook preConfigure
    export FRIDA_CORE_DEVKIT=${frida-core}/share/frida-core
    runHook postConfigure
  '';

  pythonImportsCheck = [ "frida" ];
}
