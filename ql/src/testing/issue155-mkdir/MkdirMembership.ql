/** @name Testing-only source-declared mkdir membership
 * @description Source syntax only; no runtime or flow claim.
 * @kind table
 * @id ucode/testing/issue155-mkdir-membership
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsMkdirCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  calleeIdent(call) as callee_node, call.getPathArgument() as path_node
