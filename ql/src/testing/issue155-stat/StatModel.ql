/** @name Testing-only source-declared unary stat inventory
 * @description Source syntax attribution, not a runtime target, sink or flow.
 * @kind table
 * @id ucode/testing/issue155-stat-model
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models

from SourceDeclaredFsStatCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  calleeIdent(call) as callee_node, call.getPathArgument() as argument_node
