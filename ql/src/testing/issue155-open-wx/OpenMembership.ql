/** @name Testing-only open wx model membership
 * @description Membership independent of argument projection.
 * @kind table
 * @id ucode/testing/issue155-open-wx-membership
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsOpenWxCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node
