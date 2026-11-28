/** @name Testing-only optional open read permission argument
 * @description Raw optional permission syntax, not runtime type or value.
 * @kind table
 * @id ucode/testing/issue155-open-read-permission
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsOpenReadCall call, UCODE::AstNode permission
where permission = call.getPermissionArgument()
select call.getLocation().getFile().getRelativePath() as path, call as call_node, permission as permission_node
