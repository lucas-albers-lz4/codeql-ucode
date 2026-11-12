/**
 * @name SSA identifier reaches builtin system
 * @description Additive production-pack query: a lexical SSA write's
 *              statement-level read sits on the same statement as builtin
 *              system(). Restricted to ssa_pos/ssa_neg so luci is not scored.
 *              Not request.args taint, not imported-callee flow, and not
 *              setInitAction path_found. LocalTaint stays on Models.
 *              DataFlow localFlowStep and call resolution remain none().
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/ssa-reaches-system
 * @tags testing
 */

import codeql.Locations
import codeql.files.FileSystem
import codeql.ucode.DataFlow
import codeql.ucode.m3.Models

predicate ssaFixtureFile(File f) {
  f.getBaseName() = "ssa_pos" or f.getBaseName() = "ssa_neg"
}

from Ssa::WriteDefinition def, BuiltinSystemCall sink, Location readLoc
where
  readLoc = def.getARead().getLocation() and
  ssaFixtureFile(readLoc.getFile()) and
  sink.getLocation().getFile() = readLoc.getFile() and
  sink.getLocation().getStartLine() = readLoc.getStartLine()
select def,
  def.getSourceVariable().getName() + " reaches system in " +
    readLoc.getFile().getBaseName(), sink, "system"
