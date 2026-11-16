@echo off

if defined CODEQL_UCODE_STAGED_ROOT goto staged

type NUL && "%CODEQL_EXTRACTOR_UCODE_ROOT%\tools\win64\extractor.exe" extract ^
        --file-list "%1" ^
        --source-archive-dir "%CODEQL_EXTRACTOR_UCODE_SOURCE_ARCHIVE_DIR%" ^
        --output-dir "%CODEQL_EXTRACTOR_UCODE_TRAP_DIR%"
exit /b %ERRORLEVEL%

:staged
type NUL && "%CODEQL_EXTRACTOR_UCODE_ROOT%\tools\win64\extractor.exe" extract ^
        --file-list "%1" ^
        --source-archive-dir "%CODEQL_EXTRACTOR_UCODE_SOURCE_ARCHIVE_DIR%" ^
        --output-dir "%CODEQL_EXTRACTOR_UCODE_TRAP_DIR%" ^
        --staged-root "%CODEQL_UCODE_STAGED_ROOT%"
exit /b %ERRORLEVEL%
