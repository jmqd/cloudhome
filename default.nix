with import <nixpkgs> { };
with python3Packages;
buildPythonPackage {
  pname = "cloudhome";
  version = "1.0";
  propagatedBuildInputs = [ boto3 ];
  src = ./.;
}
