{ buildPythonPackage
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

  pythonImportsCheck = [
    "frida_tools"
  ];

  strictDeps = true;

  meta.mainProgram = "frida";
}
