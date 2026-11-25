/** @name Testing-only open wx wrong-path counterfactual
 * @description Tests that the oracle rejects mode as the path.
 * @kind table
 * @id ucode/testing/issue155-open-wx-wrong-path
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsOpenWxCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  calleeIdent(call) as callee_node, call.getModeArgument() as path_node, call.getModeArgument() as mode_node
