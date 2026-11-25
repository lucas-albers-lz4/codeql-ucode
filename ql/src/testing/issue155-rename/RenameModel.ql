/** @name Testing-only source-declared two-argument rename inventory
 * @description Source attribution and argument syntax, not runtime binding or flow.
 * @kind table
 * @id ucode/testing/issue155-rename-model
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsRenameCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  calleeIdent(call) as callee_node, call.getSourceArgument() as source_node,
  call.getDestinationArgument() as destination_node
