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
import codeql.ucode.Markup

from File f
where
  (
    f instanceof UcodeFile or
    exists(UcodeMarkup::AstNode n | n.getLocation().getFile() = f)
  ) and
  not exists(ExtractionError e | e.getLocation().getFile() = f) and
  exists(f.getRelativePath())
select f, ""
