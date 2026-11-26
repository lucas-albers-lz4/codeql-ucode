/** @name Testing-only mkdir argument guard counterfactuals
 * @description Isolated arity and expression guard mutations, not production behavior.
 * @kind table
 * @id ucode/testing/issue155-mkdir-shape-mutants
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs
from UCODE::CallExpression call, string mutation
where sourceDeclaredFsCall(call, "mkdir") and
  (
    mutation = "arity" and call.getArguments().getChild(0) instanceof UCODE::Expression and
      (not exists(call.getArguments().getChild(1)) or call.getArguments().getChild(1) instanceof UCODE::Expression)
    or mutation = "path-expression" and exists(call.getArguments().getChild(0)) and
      (not exists(call.getArguments().getChild(1)) or call.getArguments().getChild(1) instanceof UCODE::Expression) and
      not exists(int i | i != 0 and i != 1 and exists(call.getArguments().getChild(i)))
    or mutation = "mode-expression" and call.getArguments().getChild(0) instanceof UCODE::Expression and
      not exists(int i | i != 0 and i != 1 and exists(call.getArguments().getChild(i)))
  )
select mutation, call.getLocation().getFile().getRelativePath() as path, call as call_node
