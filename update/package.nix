{
  lib,
  buildPythonPackage,
  setuptools,
  packaging,
}:

buildPythonPackage {
  pname = "frida-nix-update";
  version = "0.0.0";
  pyproject = true;

  src = lib.fileset.toSource {
    root = ./.;
    fileset = lib.fileset.unions [
      ./pyproject.toml
      ./src
    ];
  };

  build-system = [ setuptools ];

  dependencies = [ packaging ];

  pythonImportsCheck = [ "frida_nix_update" ];

  meta.mainProgram = "frida-nix-update";
}
