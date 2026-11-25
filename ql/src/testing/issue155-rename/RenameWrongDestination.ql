/** @name Testing-only wrong-index rename accessor mutation
 * @description Tests that the oracle rejects the first argument as the destination.
 * @kind table
 * @id ucode/testing/issue155-rename-wrong-destination
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsRenameCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  calleeIdent(call) as callee_node, call.getSourceArgument() as source_node,
  call.getSourceArgument() as destination_node
