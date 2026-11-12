/**
 * @name Extraction errors
 * @description List all extraction errors for files in the source code directory.
 * @kind diagnostic
 * @id ucode/diagnostics/extraction-errors
 */

import codeql.files.FileSystem
import codeql.ucode.Diagnostics

/** Gets the SARIF severity to associate an error. */
int getSeverity() { result = 2 }

from ExtractionError error, File f
where
  f = error.getLocation().getFile() and
  exists(f.getRelativePath())
select error, "Extraction failed in " + f + " with error " + error.getMessage(), getSeverity()
