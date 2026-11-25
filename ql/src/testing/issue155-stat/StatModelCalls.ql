/** @name Testing-only stat model call membership
 * @description Membership independent of argument projection.
 * @kind table
 * @id ucode/testing/issue155-stat-membership
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsStatCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node
