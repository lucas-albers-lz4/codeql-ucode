/**
 * @name SSA identifier reaches builtin system
 * @description Additive production-pack query: DataFlow localFlowStep from an
 *              SSA write node to a read of that same definition whose
 *              identifier is in builtin system's command
 *              argument. Restricted to ssa_pos/ssa_neg so luci is not scored.
 *              Not request.args taint, not imported-callee flow, and not
 *              setInitAction path_found. LocalTaint stays on Models.
 *              viableSourceCallable resolves unique same-file identifier
 *              and member-property FunctionDeclarations; imported
 *              luci.sys stays unresolved / inconclusive.
 *              viableLibraryCallable may resolve builtin system and
 *              imported fs popen / basename; that is not this query's
 *              localFlowStep+ evidence.
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
  read = def.getAFlowRead() and
  exists(DataFlow::SsaDefinitionNode src, DataFlow::SsaReadNode snk |
    src.getDefinition() = def and
    snk.getDefinition() = def and
    snk.getRead() = read and
    DataFlow::localFlowStep+(src, snk)
  ) and
  ssaFixtureFile(read.getFile()) and
  access.getVariable() = def.getSourceVariable() and
  toTreeSitter(access.getAstNode()).getParent*() = sink.getArgument(0) and
  read.getAstNode() = access.getAstNode()
select def,
  def.getSourceVariable().getName() + " reaches system in " + read.getFile().getBaseName(), sink,
  "system"
