{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.postgresql
    pkgs.nodejs
  ];
  env = {
    PYTHONPATH = "${pkgs.python311}/${pkgs.python311.sitePackages}";
  };
}
