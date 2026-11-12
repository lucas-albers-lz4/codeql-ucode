/**
 * @name SSA identifier reaches builtin system
 * @description Additive production-pack query: a lexical SSA write's
 *              statement-level read contains an access in builtin system's
 *              command argument. Restricted to ssa_pos/ssa_neg so luci is not scored.
 *              Not request.args taint, not imported-callee flow, and not
 *              setInitAction path_found. LocalTaint stays on Models.
 *              DataFlow localFlowStep and call resolution remain none().
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/ssa-reaches-system
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.CFG
import codeql.ucode.DataFlow
import codeql.ucode.m3.Models
private import codeql.ucode.ast.internal.AstNodes

predicate ssaFixtureFile(File f) { f.getBaseName() = "ssa_pos" or f.getBaseName() = "ssa_neg" }

from Ssa::WriteDefinition def, BuiltinSystemCall sink, CfgNode read, VariableReadAccess access
where
  read = def.getARead() and
  ssaFixtureFile(read.getFile()) and
  access.getVariable() = def.getSourceVariable() and
  toTreeSitter(access.getAstNode()).getParent*() = sink.getArgument(0) and
  sink.getParent*() = toTreeSitter(read.getAstNode()) and
  // Match the access's innermost CFG statement, as SSA does. Reads in a nested
  // function cannot stand in for an access in the enclosing statement.
  not exists(CfgNode closer |
    closer != read and
    toTreeSitter(access.getAstNode()).getParent*() = toTreeSitter(closer.getAstNode()) and
    toTreeSitter(closer.getAstNode()).getParent+() = toTreeSitter(read.getAstNode())
  )
select def,
  def.getSourceVariable().getName() + " reaches system in " + read.getFile().getBaseName(), sink,
  "system"
