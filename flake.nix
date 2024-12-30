{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonPackages = pkgs.python311Packages;
      in
      {
        devShell = pkgs.mkShell {
          buildInputs = [
            pythonPackages.python
            pythonPackages.venvShellHook
          ];
          packages = [ pkgs.poetry ];
          venvDir = "./.venv";
          postVenvCreation = ''
            unset SOURCE_DATE_EPOCH
            poetry env use .venv/bin/python
            poetry install
          '';
          postShellHook = ''
            unset SOURCE_DATE_EPOCH
            export LD_LIBRARY_PATH=${
              pkgs.lib.makeLibraryPath (
                with pkgs;
                [
                  stdenv.cc.cc
                  udev
                  xorg.libX11
                  libGL
                ]
              )
            }
            poetry env info
          '';
        };
      }
    );
}
