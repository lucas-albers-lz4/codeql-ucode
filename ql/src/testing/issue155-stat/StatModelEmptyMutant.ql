/** @name Testing-only stat missing argument guard mutation
 * @description Membership with the first-argument guard removed.
 * @kind table
 * @id ucode/testing/issue155-stat-empty-mutant
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs
from UCODE::CallExpression call
where sourceDeclaredFsCall(call, "stat") and
  not exists(int i | i != 0 and exists(call.getArguments().getChild(i)))
select call.getLocation().getFile().getRelativePath() as path, call as call_node
