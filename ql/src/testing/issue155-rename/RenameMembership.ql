/** @name Testing-only rename model membership
 * @description Membership independent of source and destination projection.
 * @kind table
 * @id ucode/testing/issue155-rename-membership
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsRenameCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node
