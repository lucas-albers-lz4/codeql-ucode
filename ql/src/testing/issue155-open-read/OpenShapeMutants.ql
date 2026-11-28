/** @name Testing-only open read argument-shape counterfactuals
 * @description Raw counterparts of arity and selected expression guards; no runtime claim.
 * @kind table
 * @id ucode/testing/issue155-open-read-shape-mutants
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs
from UCODE::CallExpression call, UCODE::String mode, string mutation
where sourceDeclaredFsCall(call, "open") and mode = call.getArguments().getChild(1) and
  mode.getChild(0).(UCODE::StringFragment).getValue() = "r" and not exists(mode.getChild(1)) and
  (
    mutation = "arity" and call.getArguments().getChild(0) instanceof UCODE::Expression and
      (not exists(call.getArguments().getChild(2)) or call.getArguments().getChild(2) instanceof UCODE::Expression)
    or mutation = "spread-path" and exists(call.getArguments().getChild(0)) and
      (not exists(call.getArguments().getChild(2)) or call.getArguments().getChild(2) instanceof UCODE::Expression) and
      not exists(int i | i != 0 and i != 1 and i != 2 and exists(call.getArguments().getChild(i)))
    or mutation = "spread-permission" and call.getArguments().getChild(0) instanceof UCODE::Expression and
      not exists(int i | i != 0 and i != 1 and i != 2 and exists(call.getArguments().getChild(i)))
  )
select mutation, call.getLocation().getFile().getRelativePath() as path, call as call_node
