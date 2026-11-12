/**
 * @name SSA definition reads
 * @description Statement-level SSA write-to-read pairs. Testing only; not a
 *              production taint query and not setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/ssa-reads
 * @tags testing
 */

import codeql.Locations
import codeql.files.FileSystem
import codeql.ucode.DataFlow

from Ssa::WriteDefinition def, Location readLoc
where readLoc = def.getARead().getLocation()
select def,
  def.getSourceVariable().getName() + ":" + def.getLocation().getStartLine().toString() + " -> " +
    readLoc.getFile().getBaseName() + ":" + readLoc.getStartLine().toString()
