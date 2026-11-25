/** @name Testing-only rename argument-shape counterfactuals
 * @description Raw-predicate counterparts of arity and expression guards, not runtime claims.
 * @kind table
 * @id ucode/testing/issue155-rename-shape-mutants
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs
from UCODE::CallExpression call, string mutation
where sourceDeclaredFsCall(call, "rename") and
  (
    mutation = "arity" and call.getArguments().getChild(0) instanceof UCODE::Expression and
      call.getArguments().getChild(1) instanceof UCODE::Expression
    or mutation = "spread-first" and exists(call.getArguments().getChild(0)) and
      call.getArguments().getChild(1) instanceof UCODE::Expression and
      not exists(int i | i != 0 and i != 1 and exists(call.getArguments().getChild(i)))
    or mutation = "spread-second" and call.getArguments().getChild(0) instanceof UCODE::Expression and
      exists(call.getArguments().getChild(1)) and
      not exists(int i | i != 0 and i != 1 and exists(call.getArguments().getChild(i)))
    or mutation = "missing" and
      not exists(int i | i != 0 and i != 1 and exists(call.getArguments().getChild(i)))
  )
select mutation, call.getLocation().getFile().getRelativePath() as path, call as call_node
