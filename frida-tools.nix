{ buildPythonPackage
, fetchPypi

, colorama
, frida
, prompt-toolkit
, pygments
}:

buildPythonPackage rec {
  pname = "frida-tools";
  version = "12.3.0";

  src = fetchPypi {
    inherit pname version;
    hash = "sha256-jtxn0a43kv9bLcY1CM3k0kf5K30Ne/FT10ohptWNwEU=";
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
