/**
 * @name Successfully extracted files
 * @description Lists all files in the source code directory that were extracted
 *   without encountering an error in the file.
 * @kind diagnostic
 * @id ucode/diagnostics/successfully-extracted-files
 * @tags successfully-extracted-files
 */

import codeql.files.FileSystem
import codeql.ucode.Diagnostics
import codeql.ucode.ast.AstNodes

from UcodeFile f
where
  not exists(ExtractionError e | e.getLocation().getFile() = f) and
  exists(f.getRelativePath())
select f, ""
