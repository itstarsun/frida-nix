metadata: final: prev:

let
  frida = import ./. { inherit metadata; pkgs = prev; };
  frida' = builtins.removeAttrs frida [ "metadata" ];
in

frida' // {
  inherit frida;

  pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
    (pythonPackages: _: {
      frida = frida.frida-python.override { inherit pythonPackages; };
      frida-tools = frida.frida-tools.override { inherit pythonPackages; };
    })
  ];
}
