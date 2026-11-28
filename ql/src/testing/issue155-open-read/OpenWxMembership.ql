/** @name Testing-only open wx membership for read-mode disjointness
 * @description Existing wx association, with no runtime or flow claim.
 * @kind table
 * @id ucode/testing/issue155-open-read-wx-membership
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.m3.Models
from SourceDeclaredFsOpenWxCall call
select call.getLocation().getFile().getRelativePath() as path, call as call_node
