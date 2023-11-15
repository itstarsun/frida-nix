final: prev:

let
  inherit (final)
    lib
    callPackage
    ;

  inherit (lib)
    recurseIntoAttrs
    ;
in

{
  frida = recurseIntoAttrs (callPackage ./. { });

  frida-tools = with final.python3Packages; toPythonApplication frida-tools;

  pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
    (pythonPackages: _:
      let
        frida = final.frida.override {
          python3Packages = pythonPackages;
        };
      in
      {
        frida = frida.frida-python;
        frida-tools = frida.frida-tools;
      }
    )
  ];
}
