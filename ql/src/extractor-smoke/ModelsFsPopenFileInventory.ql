/** Smoke-only extracted source-file inventory with explicit relative paths. */
import codeql.files.FileSystem
import codeql.ucode.Diagnostics

string extractionStatus(File f) {
  exists(ExtractionError e | e.getLocation().getFile() = f) and result = "error"
  or
  not exists(ExtractionError e | e.getLocation().getFile() = f) and result = "ok"
}

from File f
where exists(f.getRelativePath())
select f.getRelativePath(), extractionStatus(f)