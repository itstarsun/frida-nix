let
  default-metadata = builtins.fromJSON (builtins.readFile ./metadata.json);
  default-overlay = mkOverlay { };

  mkOverlay =
    { metadata ? default-metadata
    , version ? metadata.latest-release
    , tools-version ? metadata.latest-tools
    }: (final: prev:
    let
      inherit (final) fetchurl;

      mkFridaDevkit = pname:
        final.callPackage ./frida-devkit {
          inherit pname version;
          src = fetchurl metadata.releases.${version}.per-system.${final.system}.${pname};
        };
    in
    {
      frida-core = mkFridaDevkit "frida-core";
      frida-gum = mkFridaDevkit "frida-gum";
      frida-gumjs = mkFridaDevkit "frida-gumjs";

      pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
        (python-final: python-prev: {
          frida = python-final.callPackage ./frida-python {
            inherit version;
            src = fetchurl metadata.releases.${version}.frida-python;
          };

          frida-tools = python-final.callPackage ./frida-tools {
            version = tools-version;
            src = fetchurl metadata.tools.${tools-version};
          };
        })
      ];
    });
in
{
  inherit
    default-metadata
    default-overlay
    mkOverlay;
}
