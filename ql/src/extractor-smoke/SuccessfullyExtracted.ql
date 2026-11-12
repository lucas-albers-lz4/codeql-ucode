/**
 * @name Successfully extracted luci
 * @description M1 gate: exactly one successfully extracted file named luci.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/successfully-extracted-luci
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.Diagnostics

from File f
where
  not exists(ExtractionError e | e.getLocation().getFile() = f) and
  exists(f.getRelativePath()) and
  f.getBaseName() = "luci"
select f, f.getBaseName()
