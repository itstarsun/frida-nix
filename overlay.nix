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
  fridaPackages = recurseIntoAttrs (callPackage ./. { });

  frida = lib.warn "frida is renamed to fridaPackages" final.fridaPackages;

  frida-tools = with final.python3Packages; toPythonApplication frida-tools;

  pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
    (pythonPackages: _:
      let
        fridaPackages = final.fridaPackages.override {
          python3Packages = pythonPackages;
        };
      in
      {
        frida = fridaPackages.frida-python;
        frida-tools = fridaPackages.frida-tools;
      })
  ];
}
