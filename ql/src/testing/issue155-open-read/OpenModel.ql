/** @name Testing-only source-declared literal r open inventory
 * @description Source attribution and path/mode syntax, not runtime binding or flow.
 * @kind table
 * @id ucode/testing/issue155-open-read-model
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsOpenReadCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  calleeIdent(call) as callee_node, call.getPathArgument() as path_node, call.getModeArgument() as mode_node
