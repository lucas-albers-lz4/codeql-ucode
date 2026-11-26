/** @name Testing-only source-declared mkdir mode
 * @description Optional raw mode argument syntax.
 * @kind table
 * @id ucode/testing/issue155-mkdir-mode
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsMkdirCall call, UCODE::AstNode mode
where mode = call.getModeArgument()
select call.getLocation().getFile().getRelativePath() as path, call as call_node, mode as mode_node
