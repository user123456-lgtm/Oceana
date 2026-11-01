OCEANA — WINDOWS SELF-CONTAINED BUILD

This project is configured to create OCEANA-Setup.exe on a Windows build runner.
The person installing the resulting OCEANA-Setup.exe does NOT need Python.

IMPORTANT: This ZIP is build source, NOT the finished installer. This environment
cannot run a Windows build or verify the final .exe. The GitHub Actions workflow
in .github/workflows/build-windows.yml creates the installer artifact on Windows.

To obtain the installer:
1. Upload the contents of this folder to a new GitHub repository.
2. Open the repository's Actions tab.
3. Choose 'Build OCEANA Windows installer' and click 'Run workflow'.
4. When the workflow finishes successfully, open its run and download
   'OCEANA-Windows-Installer' from Artifacts.
5. Extract OCEANA-Setup.exe and run it. No Python is needed on the install PC.

OCEANA is a standalone Lua editor/runtime. It does not inject into Roblox or
provide Roblox-only globals such as game, workspace, or Instance.
