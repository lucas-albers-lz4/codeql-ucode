/** @name Testing-only mkdir class membership without argument projection
 * @description Detects class members even if they have no path argument.
 * @kind table
 * @id ucode/testing/issue155-mkdir-class-membership
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsMkdirCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  calleeIdent(call) as callee_node
