{
  description = "DevOps Info Service reproducible builds with Nix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = import ./default.nix { inherit pkgs; };
          dockerImage = import ./docker.nix { inherit pkgs; };
        });

      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          python = pkgs.python312.withPackages (ps: with ps; [
            fastapi
            prometheus-client
            uvicorn
          ]);
        in
        {
          default = pkgs.mkShell {
            packages = [
              python
              pkgs.curl
            ];
          };
        });
    };
}
