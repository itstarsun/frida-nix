metadata: final: prev:

let
  frida' = prev.callPackage ./. { inherit metadata; };
  frida = builtins.removeAttrs frida' [ "overlay" ];
in

{
  inherit frida;

  inherit (frida)
    frida-core
    frida-gum
    frida-gumjs
    ;

  pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
    (pythonPackages: _: {
      frida = frida.frida-python.override { inherit pythonPackages; };
      frida-tools = frida.frida-tools.override { inherit pythonPackages; };
    })
  ];
}
