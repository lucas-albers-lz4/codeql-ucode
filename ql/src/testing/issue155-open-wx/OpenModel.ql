/** @name Testing-only source-declared literal wx open inventory
 * @description Source attribution and path/mode syntax, not runtime binding or flow.
 * @kind table
 * @id ucode/testing/issue155-open-wx-model
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsOpenWxCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  calleeIdent(call) as callee_node, call.getPathArgument() as path_node, call.getModeArgument() as mode_node
