{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = [
    pkgs.act
    pkgs.openssl
    pkgs.python3
    pkgs.watchexec
  ];
}
