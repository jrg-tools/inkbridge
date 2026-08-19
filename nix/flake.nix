{
  description = "inkbridge development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-compat.url = "github:NixOS/flake-compat";
  };

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          # Detect the project root from wherever the user entered the shell,
          # so commands work from the repository root or any subdirectory.
          # Using `git rev-parse` to do so (assuming git is installed
          # system-wide); user can overwrite this by setting PROJECT_ROOT env.
          setEnvs = ''
            PROJECT_ROOT="''${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
            export PROJECT_ROOT
            export PLATFORMIO_CORE_DIR="$PROJECT_ROOT/.cache/platformio"
          '';
          venvBootstrap = ''
            export PATH="$PROJECT_ROOT/.venv/bin:$PATH"

            if [ ! -x "$PROJECT_ROOT/.venv/bin/pio" ]; then
              echo "Creating .venv and installing PlatformIO Core..."
              # --seed installs pip; PlatformIO shells out to pip when
              # installing tool packages (e.g. tool-esptoolpy).
              uv venv --seed "$PROJECT_ROOT/.venv" &&
              uv pip install --python "$PROJECT_ROOT/.venv/bin/python" \
                -U platformio ||
              echo "Failed to install PlatformIO Core" >&2
            fi
          '';
          # Linux only: PlatformIO's downloaded ESP32 toolchain binaries are
          # prebuilt for an FHS /lib layout. On darwin they run natively.
          fhsEnv = pkgs.buildFHSEnv {
            name = "inkbridge-shell";

            targetPkgs =
              pkgs: with pkgs; [
                python3
                uv

                # Runtime libraries used by PlatformIO's downloaded ESP32 toolchain binaries.
                stdenv.cc.cc.lib
                zlib
                ncurses
              ];

            profile = ''
              ${setEnvs}
              ${venvBootstrap}
            '';
          };
          pio = pkgs.writeShellScriptBin "pio" ''
            exec ${fhsEnv}/bin/inkbridge-shell -c 'exec pio "$@"' pio "$@"
          '';
          # Web UI (web/) is a SvelteKit app built with pnpm.
          webTools = with pkgs; [
            nodejs_24
            pnpm
          ];
          # Quick commands. `pio` resolves from PATH: the FHS shim on Linux,
          # the .venv on darwin (both set up by the shell hooks).
          mkCmd =
            name: script:
            pkgs.writeShellScriptBin name ''
              set -euo pipefail
              PROJECT_ROOT="''${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
              cd "$PROJECT_ROOT"
              ${script}
            '';
          commands = [
            # Build the SvelteKit UI and stage it into data/.
            (mkCmd "build-ui" ''
              cd web
              pnpm install
              pnpm run deploy
            '')
            # Build UI + flash the LittleFS partition.
            (mkCmd "flash-ui" ''
              build-ui
              pio run -t uploadfs
            '')
            # Flash the firmware.
            (mkCmd "flash" ''
              pio run -t upload
            '')
            # Flash the firmware and attach the serial monitor.
            (mkCmd "flash-monitor" ''
              pio run -t upload
              exec pio device monitor
            '')
            # Flash everything: UI + filesystem + firmware, then monitor.
            (mkCmd "flash-all" ''
              build-ui
              pio run -t uploadfs
              pio run -t upload
              exec pio device monitor
            '')
          ];
        in
        {
          default = pkgs.mkShell {
            packages =
              (
                if pkgs.stdenv.isLinux then
                  [
                    pio
                    fhsEnv
                  ]
                else
                  [ pkgs.uv ]
              )
              ++ webTools
              ++ commands
              ++ [
                pkgs.clang-tools # for clang-format
              ];

            shellHook = if pkgs.stdenv.isLinux then setEnvs else setEnvs + venvBootstrap;
          };
        }
      );
    };
}
