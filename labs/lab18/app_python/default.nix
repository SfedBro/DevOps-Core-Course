{ pkgs ? import <nixpkgs> {} }:

let
  python = pkgs.python312.withPackages (ps: with ps; [
    fastapi
    prometheus-client
    uvicorn
  ]);
in
pkgs.stdenv.mkDerivation {
  pname = "devops-info-service";
  version = "1.0.0";
  src = ./.;

  nativeBuildInputs = [ pkgs.makeWrapper ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/share/devops-info-service $out/bin
    cp app.py requirements.txt $out/share/devops-info-service/

    makeWrapper ${python}/bin/python $out/bin/devops-info-service \
      --add-flags "$out/share/devops-info-service/app.py" \
      --set-default HOST "0.0.0.0" \
      --set-default PORT "5000" \
      --set-default APP_ENV "nix"

    runHook postInstall
  '';

  meta = {
    description = "FastAPI DevOps Info Service built reproducibly with Nix";
    mainProgram = "devops-info-service";
  };
}
