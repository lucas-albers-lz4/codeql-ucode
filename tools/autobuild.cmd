@echo off

type NUL && "%CODEQL_EXTRACTOR_UCODE_ROOT%\tools\%CODEQL_PLATFORM%\extractor" autobuild

exit /b %ERRORLEVEL%