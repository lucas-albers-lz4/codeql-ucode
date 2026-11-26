/** @name Testing-only wrong mkdir path slot
 * @description Mutation to test the path identity oracle.
 * @kind table
 * @id ucode/testing/issue155-mkdir-wrong-path
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsMkdirCall call, UCODE::AstNode mode
where mode = call.getModeArgument()
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  calleeIdent(call) as callee_node, mode as path_node
