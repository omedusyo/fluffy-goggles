{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = [
    pkgs.openssl
    pkgs.python3
    pkgs.watchexec
  ];
}
